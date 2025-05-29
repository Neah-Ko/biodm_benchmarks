"""Authorization and API call logs"""
import datetime
from functools import wraps
from flask import request
import jwt
from jwcrypto import jwk
from keycloak.keycloak_openid import KeycloakOpenID


from server.app import app, db
from server.model import History

idrsa = app.config["IDRSA"]
options = app.config["JWT_OPTIONS"]
public_key = (
    "-----BEGIN PUBLIC KEY-----\n" + idrsa + "\n-----END PUBLIC KEY-----"
)


kc_conn = KeycloakOpenID(
    server_url=app.config["AUTH_BASE_URL"],
    realm_name=app.config["AUTH_REALM"],
    client_id=app.config["KC_CLIENT_ID"],
    client_secret_key=str(app.config["KC_CLIENT_SECRET"]),
)

def extract_token_header(request):
    token = request.headers.get("Authorization", None)

    if not token:
        return None

    if 'bearer' in token:
        return token.split("bearer")[-1]

    if 'Bearer' in token:
        return token.split("Bearer")[-1]

    token = token.replace(' ', '')

    assert token.startswith('ey')

    return token


def decode_token(token: str):
    """Decode token."""
    def enclose_idrsa(idrsa) -> str:
        key = (
            "-----BEGIN PUBLIC KEY-----\n"
            + idrsa
            + "\n-----END PUBLIC KEY-----"
        ).encode('utf-8')
        return jwk.JWK.from_pem(key)

    try:
        token = token.replace(' ', '')
        return kc_conn.decode_token(
            token, key=enclose_idrsa(idrsa) #, options=self.jwt_options
        )
    except Exception as e:
        raise Exception(f"Invalid Token: {str(e)}")

def get_public_key():
    """
    Gets the public key from the KC_PUBLIC_KEY environment variable.
    Parameters:
    kc_key (str): The public key from the environment variable.
    Returns:
    The public key loaded from the certificate string.
    """
    idrsa = app.config["IDRSA"]
    public_key = (
        "-----BEGIN PUBLIC KEY-----\n" + idrsa + "\n-----END PUBLIC KEY-----"
    )
    return public_key


def extract_items(token, name):
    """
    Get information from Keycloak like e.g. keycloak groups
    """
    if token.get(name) is not None:
        return [s.replace("/", "") for s in token.get(name)]
    return []


def get_token(func):
    """
    Get token from request header
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        token = request.headers["Authorization"]
        return func(token=token, *args, **kwargs)

    return decorated_function


# TODO
# refactor below
def login_required(func):
    """
    Decorator for handling keycloak login
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        token = extract_token_header(request)

        # token = request.headers.get("Authorization")
        groups = []

        if token is None:
            return {"message": "No token provided"}, 401
        public_key = get_public_key()
        try:
            decoded = decode_token(token)
            # decoded = jwt.decode(
            #     token, public_key, algorithms="RS256", options=options
            # )
            groups = [s.replace("/", "") for s in decoded.get("groups")]

        except jwt.exceptions.InvalidSignatureError as err:
            print(err, "check if the public key is correct")
            print("public key:", public_key)
            return {"message": f"{err}"}, 500

        # Check if changing the cryptograph version helps
        except jwt.exceptions.InvalidAlgorithmError as e:
            # If this exception is triggered it is likely
            # that the installed cryptography version is wrong
            # supported versions = [3.4.7]
            return {"message": f"{e}"}, 500

        except jwt.exceptions.DecodeError as e:
            # If this exception is triggered it is likely
            # that the token has a invalid header or cryptopadding`
            return {"message": f"{e}"}, 500

        except Exception as e:
            return {
                "message": f"Something went wrong {e} {e.__class__.__name__}"
            }, 500
        userid = decoded.get("preferred_username")
        groups = extract_items(decoded, "groups")  # keycloak groups

        # TODO
        # raise exception if groups is an empty list
        # which happens if the token is already expired

        timestamp = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
        print(
            "\t".join(
                [
                    timestamp,
                    userid,
                    ",".join(groups),
                    f"{request.url}-{request.method}",
                ]
            )
        )

        return func(userid=userid, groups=groups, *args, **kwargs)

    return decorated_function


@app.after_request
def history(response):
    """
    Record any request and save it in history table (on postgres)
    """
    # pylint Too many nested blocks (7/5) (too-many-nested-blocks)
    if request.method != "OPTIONS" and "Authorization" in request.headers:

        # token = request.headers["Authorization"]
        token = extract_token_header(request)

        groups = []
        try:
            token = token.replace(' ', '')
            decoded = decode_token(token)
            # decoded = jwt.decode(
            #     token, public_key, algorithms="RS256", options=options
            # )
            groups = [s.replace("/", "") for s in decoded.get("groups")]

        except jwt.exceptions.InvalidAlgorithmError as e:
            return {"message": f"{e}"}, 500

        except Exception as e:
            return {
                "message": f"Something went wrong {e} {e.__class__.__name__}"
            }, 500

        userid = decoded.get("preferred_username")
        groups = extract_items(decoded, "group")
        timestamp = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")

        splitted = request.url.split("/")
        entity_id = splitted[len(splitted) - 1]
        content = {"data": "empty"}
        updated_content = {"data": "updated"}

        if request.method == "POST":
            content["data"] = request.json
            if not content["data"] and isinstance(request.data, bytes):
                import json
                content["data"] = json.loads(request.data)

            if response.status == "200 OK":
                try:
                    # If uploading JSON or Excel
                    if isinstance(response.json, list):
                        for ent in range(0, len(response.json)):
                            entity_id = response.json[ent]["id"]
                            insert_history_entry(
                                entity_id,
                                userid,
                                groups,
                                request,
                                {"data": "uploaded"},
                            )
                    # If creating manually
                    # else:
                    #     entity_id = response.json["id"]

                # pylint Catching too general exception Exception
                except Exception as e:
                    print("POST without ID in the response", e)

        if request.method == "PUT" and response.status == "200 OK":
            try:
                content = updated_content
            except Exception as e:
                print("PUT without ID in the response", e)

        # Save to db
        insert_history_entry(entity_id, userid, groups, request, content)

        print(
            "\t".join(
                [
                    timestamp,
                    userid,
                    ",".join(groups),
                    f"{request.url}-{request.method}",
                ]
            )
        )
    return response


# Create History entry
def insert_history_entry(entity_id, userid, groups, req, content):
    """
    insert request into history table (in postgres)
    """

    his = History(
        entity_id=entity_id,
        timestamp=datetime.datetime.now(),
        username=userid,
        groups=",".join(groups),
        endpoint=req.url,
        method=req.method,
        content=content,
    )

    try:
        his.save_to_db()

    # pylint Instance of 'scoped_session' has no 'rollback' member (no-member)
    except Exception as e:
        print(e)
        db.session.rollback()
