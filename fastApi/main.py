import uvicorn
# from contextlib import asynccontextmanager
from typing import List, Callable, Any, Dict
from time import sleep
from datetime import datetime
import logging

from fastapi import FastAPI, Path, Depends, Request
from fastapi.responses import RedirectResponse
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from sqlalchemy.exc import IntegrityError
from starlette.authentication import BaseUser
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send


from fastapi_keycloak import OIDCUser, FastAPIKeycloak 
from fastapi_keycloak_middleware import KeycloakConfiguration, AuthorizationMethod, setup_keycloak_middleware, get_user


from db import DatabaseManager
from crud import read, create, read_all
from models import ProjectSchema, ProjectCreateSchema, History


SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8002

KC_HOST="http://10.10.0.3:8080"
KC_REALM="3TR"
KC_PUBLIC_KEY="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0juOxC3+S97HFnlmRgWqUaSpTlscaH6IQaoLuqXFYakDJCV6WU0andDRQFJH8CeOaiVx84J1g7m/cNzxX6Ilz+0MZ6mnBFShaGY0+Qk6zIipFU2ehWQtAm0IWGwQipXC2enlXLIglRXJJepH7jOxC+fyY+f++09+68KuNAAUL8IjvZRMCu/AV3qlm6zdeCztTxy8eiBH9shg+wNLRpWczfMBAHetqqpzy9kVhVizHFdSxd21yESRce7iUQn+KzwsGzBve0Ds68GzhgyUXYjXV/sQ3jaNqDAy+qiCkv0nXKPBxVFUstPQQJvhlQ4gZW7SUdIV3IynBXckpGQhE24tcQIDAQAB"
KC_CLIENT_ID="submission_client"
KC_CLIENT_SECRET="38wBvfSVS7fa3LprqSL5YCDPaMUY1bTl"
ADMIN_CLI_SECRET="7krQPByionhtTxULwnDSQNPtvyxiUbKX"

app = FastAPI()



# keycloak_config = KeycloakConfiguration(
#     url=KC_HOST,
#     realm=KC_REALM,
#     client_id=KC_CLIENT_ID,
#     client_secret=KC_CLIENT_SECRET,
#     verify=False,
#     required_claims=[]
# )
idp = FastAPIKeycloak(
    server_url=KC_HOST,
    realm=KC_REALM,
    client_id=KC_CLIENT_ID,
    client_secret=KC_CLIENT_SECRET,
    admin_client_id="master-realm",
    admin_client_secret=ADMIN_CLI_SECRET,
    callback_uri=f"http://{SERVER_HOST}:{SERVER_PORT}/syn_ack"
)
idp.add_swagger_config(app)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Middlewares
from starlette.authentication import (
    BaseUser, UnauthenticatedUser
)
from starlette.requests import HTTPConnection


class AnonUser(UnauthenticatedUser):
    @property
    def display_name(self) -> str:
        return "anon"

    @property
    def groups(self) -> List[str]:
        return []


class KeycloakUser(BaseUser):
    def __init__(self, token_data: dict):
        self.token_data = token_data

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.token_data.get("preferred_username", "unknown")

    @property
    def groups(self) -> List[str]:
        return self.token_data.get("groups", [])

    @property
    def roles(self):
        return self.token_data.get("realm_access", {}).get("roles", [])


class AuthenticationMiddleware:
    """Handle token decoding for incoming requests, populate request object with result."""
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        def decode_token(conn: HTTPConnection):
            header = conn.headers.get("Authorization")
            if not header or not header.lower().startswith("bearer"):
                return AnonUser()
            token = (header.split("Bearer")[-1] if "Bearer" in header else header).strip()
            try:
                return KeycloakUser(idp._decode_token(token))
            except:
                return AnonUser()

        if scope["type"] not in ["http", "websocket"]:
            await self.app(scope, receive, send)
            return

        conn = HTTPConnection(scope)
        scope["user"] = decode_token(conn)
        await self.app(scope, receive, send)


# pylint: disable=too-few-public-methods
class HistoryMiddleware(BaseHTTPMiddleware):
    """Log incomming requests into History table AND stdout."""
    def __init__(self, app: ASGIApp, server_host: str) -> None:
        self.server_host = server_host
        super().__init__(app, self.dispatch)

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        async def write(entry: Dict[str, Any]):
            async with app.db.session() as s:
                s.add(History(**entry))
                await s.commit()

        endpoint = str(request.url).rsplit(self.server_host, maxsplit=1)[-1]
        body = await request.body()
        username = request.user.display_name
        entry = {
            'user_username': username,
            'endpoint': endpoint,
            'method': request.method,
            'content': str(body) if body else ""
        }
        try:
            await write(entry)
        except IntegrityError as _:
            # Collision may happen in case two anonymous requests hit at the exact same tick.
            try: # Try once more.
                sleep(0.1)
                await write(entry)
            except Exception as _:
                # Keep going in any case. History feature should not be blocking.
                pass

        # Log
        timestamp = datetime.now().strftime("%I:%M%p on %B %d, %Y")
        logger.info(
            f'{timestamp}\t{username}\t{",".join(request.user.groups)}\t'
            f'{endpoint}\t-\t{request.method}'
        )

        return await call_next(request)


# Add middlewares
app.add_middleware(HistoryMiddleware, server_host=SERVER_HOST)
app.add_middleware(AuthenticationMiddleware)
# setup_keycloak_middleware(
#     app,
#     keycloak_configuration=keycloak_config,
#     exclude_patterns=["/live", "/login", "/syn_ack"],
# )


# STARTUP
@app.on_event('startup')
async def startup():
    app.db = DatabaseManager()
    await app.db.init_db()


# @asynccontextmanager
# async def lifespan(app):
#     """ background task starts at statrup """
#     # await connect_db(app)
#     # # asyncio.create_task(connect_db())
#     # yield
#     print("on")
#     yield
#     print("off")


# ENDPOINTS
@app.get("/live")
def live():
    """Liveness endpoint"""
    return "live"


@app.get("/projects", response_model=List[ProjectSchema], status_code=status.HTTP_200_OK)
async def get_projects(request: Request, short_name: str=None):#, user: OIDCUser = Depends(idp.get_current_user())):
# async def get_projects(short_name: str=None, user: OIDCUser = Depends(get_user)):
    # assert user
    # assert request.user
    assert (request.user and isinstance(request.user, KeycloakUser))
    async with app.db.session() as s:
        return await read_all(s, short_name)


@app.get("/projects/{id}", response_model=ProjectSchema, status_code=status.HTTP_200_OK)
async def get_project(request: Request, id: int = Path(gt=0)):#, user: OIDCUser = Depends(idp.get_current_user())):
# async def get_project(id: int = Path(gt=0), user: OIDCUser = Depends(get_user)):
    # assert request.user
    assert (request.user and isinstance(request.user, KeycloakUser))
    async with app.db.session() as s:
        return await read(s, id)


@app.post("/projects", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
async def create_project(request: Request, item: ProjectCreateSchema):#, user: OIDCUser = Depends(idp.get_current_user())):#(item: ProjectCreateSchema):
# async def create_project(item: ProjectCreateSchema, user: OIDCUser = Depends(get_user)):#(item: ProjectCreateSchema):
    assert (request.user and isinstance(request.user, KeycloakUser))
    async with app.db.session() as s:
        return await create(s, item)


# https://fastapi-keycloak.code-specialist.com/quick_start/
@app.get("/login")
def login_redirect():
    return RedirectResponse(idp.login_uri)


@app.get("/syn_ack")
def callback(session_state: str, code: str):
    return idp.exchange_authorization_code(session_state=session_state, code=code)  # This will return an access token


def main():
    return app


if __name__ == "__main__":
    uvicorn.run(
        f"{__name__}:main",
        factory=True,
        host=SERVER_HOST,
        port=SERVER_PORT,
        lifespan="on",
        loop="uvloop",
        proxy_headers=True,
        forwarded_allow_ips='*',
        log_level="debug",
        access_log=False
    )
