from django import User
from rest_framework.authentication import BaseAuthentication  
from jwcrypto import jwk
from keycloak.openid_connection import KeycloakOpenIDConnection
from keycloak.keycloak_openid import KeycloakOpenID


KC_HOST="http://10.10.0.3:8080"
KC_REALM="3TR"
KC_PUBLIC_KEY="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0juOxC3+S97HFnlmRgWqUaSpTlscaH6IQaoLuqXFYakDJCV6WU0andDRQFJH8CeOaiVx84J1g7m/cNzxX6Ilz+0MZ6mnBFShaGY0+Qk6zIipFU2ehWQtAm0IWGwQipXC2enlXLIglRXJJepH7jOxC+fyY+f++09+68KuNAAUL8IjvZRMCu/AV3qlm6zdeCztTxy8eiBH9shg+wNLRpWczfMBAHetqqpzy9kVhVizHFdSxd21yESRce7iUQn+KzwsGzBve0Ds68GzhgyUXYjXV/sQ3jaNqDAy+qiCkv0nXKPBxVFUstPQQJvhlQ4gZW7SUdIV3IynBXckpGQhE24tcQIDAQAB"
KC_CLIENT_ID="submission_client"
KC_CLIENT_SECRET="38wBvfSVS7fa3LprqSL5YCDPaMUY1bTl"
# ADMIN_CLI_SECRET="7krQPByionhtTxULwnDSQNPtvyxiUbKX"


class KeycloakManager:
    """Manages a service account connection and an admin connection.
    Use the first to authenticate tokens and the second to manage the realm.
    """
    def __init__(
        self,
        host: str,
        realm: str,
        public_key: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self.host = host
        self.realm = realm
        self.public_key = public_key
        try:
            self._openid = KeycloakOpenID(
                server_url=host,
                realm_name=realm,
                client_id=client_id,
                client_secret_key=str(client_secret),
            )
        except Exception as e:
            raise Exception(
                f"Failed to initialize connection to Keycloak: {e.error_message}"
            )

    @property
    def openid(self):
        """Service account connection."""
        return self._openid

    @property
    def endpoint(self):
        return self.openid.connection.base_url

    async def auth_url(self, redirect_uri: str):
        """Authentication URL."""
        return await self.openid.a_auth_url(redirect_uri=redirect_uri, scope="openid", state="")

    async def redeem_code_for_token(self, code: str, redirect_uri: str):
        """Code for token."""
        return await self.openid.a_token(
            grant_type="authorization_code", code=code, redirect_uri=redirect_uri
        )

    def decode_token(self, token: str):
        """Decode token."""
        def enclose_idrsa(idrsa) -> str:
            key = (
                "-----BEGIN PUBLIC KEY-----\n"
                + idrsa
                + "\n-----END PUBLIC KEY-----"
            ).encode('utf-8')
            return jwk.JWK.from_pem(key)

        try:
            return self.openid.decode_token(
                token, key=enclose_idrsa(self.public_key) #, options=self.jwt_options
            )
        except Exception as e:
            raise Exception(f"Invalid Token: {str(e)}")


# https://stackademic.com/blog/integrating-keycloak-with-django-7ae39abe3a0b
class KeycloakAuthentication(BaseAuthentication):
    def __init__(self):
        super().__init__()
        self.kc = KeycloakManager(
            host=KC_HOST,
            realm=KC_REALM,
            public_key=KC_PUBLIC_KEY,
            client_id=KC_CLIENT_ID,
            client_secret=KC_CLIENT_SECRET,
        )

    def authenticate(self, request):  
        # Your authentication logic here using python-keycloak  
        # Example:
        token = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[-1]  
        user_info = self.kc.decode_token(token)  

        # Create or retrieve Django user based on user_info  
        # Example:  
        user, created = User.objects.get_or_create(username=user_info['preferred_username'])  

        return user, None