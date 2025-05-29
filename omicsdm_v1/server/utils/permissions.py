import requests
from requests.exceptions import Timeout

from server.app import app
from server.utils.error_handler import ServiceUnavailable
# from server.security import kc_conn
from server.app import app

from keycloak.keycloak_admin import KeycloakAdmin
from keycloak.openid_connection import KeycloakOpenIDConnection

cfg = app.config


def kc_admin(token):
    conn = KeycloakOpenIDConnection(
        realm_name=app.config["AUTH_REALM"],
        server_url=app.config["AUTH_BASE_URL"],
        token={
            'access_token': token,
            'expires_in': 3600,
        },
        verify=True
    )
    return KeycloakAdmin(connection=conn)


def clean_token(token):
    if not token:
        return None

    if 'bearer' in token:
        return token.split("bearer")[-1]

    if 'Bearer' in token:
        return token.split("Bearer")[-1]

    token = token.replace(' ', '')

    assert token.startswith('ey')

    return token


def get_all_kc_groups(token):
    """
    Get all groups from keycloak
    and check if the group is in the list
    """
    token = clean_token(token).replace(' ',  '')
    admin = kc_admin(token)

    # url = f"{cfg['AUTH_BASE_URL']}/admin/realms/{cfg['AUTH_REALM']}/groups"
    # headers = {"Authorization": f"Bearer {token}"}

    try:
        response = admin.get_groups()
        # response = requests.get(  # nosec (for now, should be changed)
        #     url, headers=headers, verify=False, timeout=10
        # )
    except Timeout:
        print("Timeout has been raised.")

    # TODO
    # return the error message that the user is not configured
    # correctly. Please contact the keycloak adminstrators to resolve this

    # if response.status_code == 403:
    #     raise ServiceUnavailable("Service unavailable")

    # if response.status_code != 200:
    #     raise ServiceUnavailable(
    #         "Keycloak",
    #         response.text,
    #         response.reason,
    #         status_code=response.status_code,
    #     )

    groups = [res["name"] for res in response] #.json()]
    groups.remove("admin")
    return groups


def is_valid_kc_group(group_name, token):
    """
    Get all groups from keycloak
    and check if the group is in the list
    """
    groups = get_all_kc_groups(token)
    return group_name in groups
