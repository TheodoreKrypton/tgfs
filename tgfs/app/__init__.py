import base64
import uuid
from contextvars import ContextVar
from http import HTTPStatus
from typing import Any, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tgfs.auth import auth_basic, auth_bearer
from tgfs.auth import login as login_bearer
from tgfs.config import Config
from tgfs.core.client import Client

from .manager import create_manager_app
from .webdav import METHODS, create_webdav_app

READONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PROPFIND"})


def cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=list(METHODS),
        allow_headers=["*"],
    )
    return app


def create_app(client: Client, config: Config) -> FastAPI:
    app = FastAPI()
    cors(app)

    uuid_context = ContextVar("uuid", default="")

    @app.middleware("http")
    async def add_uuid_middleware(
        request: Request, call_next: Callable[[Any], Any]
    ) -> Any:
        uuid_context.set(str(uuid.uuid4()))
        return await call_next(request)

    def UNAUTHORIZED(detail: str) -> Response:
        return Response(
            status_code=HTTPStatus.UNAUTHORIZED,
            content=detail,
        )

    def FORBIDDEN(detail: str) -> Response:
        return Response(
            status_code=HTTPStatus.FORBIDDEN,
            content=detail,
        )

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next: Callable[[Any], Any]) -> Any:
        if request.method == "OPTIONS" or request.url.path == "/login":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return UNAUTHORIZED("Authorization header is missing")
        try:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                user = auth_bearer(token)
            elif auth_header.startswith("Basic "):
                credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
                username, password = credentials.split(":", 1)
                user = auth_basic(username, password)

            else:
                return UNAUTHORIZED("Unsupported authentication method")

            if request.method not in READONLY_METHODS and user.readonly:
                # reject readonly users for non-readonly methods
                return FORBIDDEN("You do not have permission to perform this action")
            return await call_next(request)

        except Exception as e:
            return UNAUTHORIZED(str(e))

    class LoginRequest(BaseModel):
        username: str
        password: str = ""

    @app.post(path="/login")
    async def login(request: Request, body: LoginRequest):
        try:
            return {"token": login_bearer(body.username, body.password)}
        except Exception as e:
            return UNAUTHORIZED(str(e))

    manager_app = cors(create_manager_app(client, config))
    app.mount("/api", manager_app)

    webdav_app = cors(create_webdav_app(client, "/webdav"))
    app.mount("/webdav", webdav_app)

    return app
