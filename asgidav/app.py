import asyncio
import base64
import logging
import time
import uuid
from collections.abc import Awaitable
from contextvars import ContextVar
from http import HTTPStatus
from typing import Any, Callable, Optional, TypedDict
from urllib.parse import unquote, urlparse

import jwt
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from .folder import Folder
from .member import Member
from .reqres import PropfindRequest, propfind
from .resource import Resource
from .utils import calc_content_length

logger = logging.getLogger(__name__)
LOCK_TOKEN = "opaquelocktoken:dummy-lock-id"


def split_path(path: str) -> tuple[str, str]:
    path = path.strip("/")
    parts = path.rsplit("/", 1)
    if len(parts) == 1:
        return "/", parts[0]
    return parts[0], parts[1]


def extract_path_from_destination(destination: str) -> str:
    if destination.startswith(("http://", "https://")):
        parsed = urlparse(destination)
        path = parsed.path
    else:
        path = destination
    return unquote(path)


class JWTConfig(TypedDict):
    secret: str
    algorithm: str
    life: int


def create_app(
    get_member: Callable[[str], Awaitable[Optional[Member]]],
    jwt_config: JWTConfig,
    auth_callback: Optional[Callable[[str, str], bool]] = None,
) -> FastAPI:
    async def root() -> Folder:
        res = await get_member("/")
        if not res or not isinstance(res, Folder):
            raise ValueError("/ is not a Folder")
        return res

    common_headers = {
        "DAV": "1, 2",
        "WWW-Authenticate": 'Basic realm="WebDAV"',
        "MS-Author-Via": "DAV",
    }

    ALLOWED_METHODS = [
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
        "PROPFIND",
        "COPY",
        "MOVE",
        "MKCOL",
        "LOCK",
        "UNLOCK",
    ]

    NOT_FOUND = HTTPException(status_code=HTTPStatus.NOT_FOUND)
    CREATED = Response(status_code=HTTPStatus.CREATED, headers=common_headers)
    NO_CONTENT = Response(status_code=HTTPStatus.NO_CONTENT, headers=common_headers)
    UNAUTHORIZED = Response(
        status_code=HTTPStatus.UNAUTHORIZED.value,
        content="Unauthorized",
        headers=common_headers
        | {
            "Content-Type": "text/html",
            "WWW-Authenticate": 'Basic realm="TGFS WebDAV Server"',
        },
    )

    class CONFLICT(HTTPException):
        status_code = HTTPStatus.CONFLICT

        def __init__(self, detail: str):
            super().__init__(status_code=self.status_code, detail=detail)

    class BAD_REQUEST(HTTPException):
        status_code = HTTPStatus.BAD_REQUEST

        def __init__(self, detail: str):
            super().__init__(status_code=self.status_code, detail=detail)

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=["*"],
    )

    uuid_context = ContextVar("uuid", default="")

    @app.middleware("http")
    async def add_uuid_middleware(
        request: Request, call_next: Callable[[Any], Any]
    ) -> Any:
        uuid_context.set(str(uuid.uuid4()))
        return await call_next(request)

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next: Callable[[Any], Any]) -> Any:
        if (
            auth_callback
            and request.method not in {"OPTIONS"}
            and request.url.path != "/login"
        ):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return UNAUTHORIZED
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                try:
                    if not jwt.decode(
                        token,
                        key=jwt_config["secret"],
                        algorithms=[jwt_config["algorithm"]],
                        options={"verify_exp": True},
                    ):
                        return UNAUTHORIZED
                except Exception as e:
                    logger.error(e)
                    return UNAUTHORIZED
            elif auth_header.startswith("Basic "):
                try:
                    credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
                    username, password = credentials.split(":", 1)
                    if not auth_callback(username, password):
                        return UNAUTHORIZED
                except (ValueError, UnicodeDecodeError):
                    return UNAUTHORIZED
            else:
                return UNAUTHORIZED
        return await call_next(request)

    class LoginRequest(TypedDict):
        username: str
        password: str

    @app.post(path="/login")
    async def login(request: Request):
        data: LoginRequest = await request.json()
        username = data["username"] if auth_callback else "anonymous"
        if auth_callback and not auth_callback(username, data["password"]):
            return UNAUTHORIZED
        jwt_token = jwt.encode(
            {
                "username": username,
                "exp": int(time.time()) + jwt_config["life"],
            },
            key=jwt_config["secret"],
            algorithm=jwt_config["algorithm"],
        )
        return {"token": jwt_token}

    @app.options(path="/{path:path}")
    async def options():
        return Response(
            status_code=HTTPStatus.OK,
            headers=common_headers
            | {
                "Allow": ", ".join(ALLOWED_METHODS),
                "Content-Length": "0",
                "Cache-Control": "no-cache",
            },
        )

    @app.api_route("/{path:path}", methods=["PROPFIND"])
    async def handle_propfind(request: Request, path: str):
        r = await PropfindRequest.from_request(request)
        if member := await get_member(path):
            resp = await propfind((member,), r.depth, r.props)
            return Response(
                resp,
                status_code=HTTPStatus.MULTI_STATUS,
                media_type="application/xml; charset=utf-8",
                headers=common_headers
                | {"Content-Type": "application/xml; charset=utf-8"},
            )
        raise NOT_FOUND

    @app.head("/{path:path}")
    async def head(request: Request, path: str):
        if member := await get_member(path):
            if isinstance(member, Folder):
                return Response(
                    status_code=HTTPStatus.OK,
                    headers=common_headers
                    | {
                        "Content-Type": "httpd/unix-directory",
                        "Last-Modified": str(await member.last_modified()),
                        "Accept-Ranges": "none",
                    },
                )
            content_length, content_type, last_modified = await asyncio.gather(
                member.content_length(),
                member.content_type(),
                member.last_modified(),
            )
            return Response(
                status_code=HTTPStatus.OK,
                headers=common_headers
                | {
                    "Content-Type": content_type,
                    "Content-Length": str(content_length),
                    "Last-Modified": str(last_modified),
                },
            )
        raise NOT_FOUND

    @app.get("/{path:path}")
    async def get(request: Request, path: str):
        begin, end = 0, -1
        is_range_request = False

        if "Range" in request.headers:
            range_header = request.headers["Range"]
            if range_header.startswith("bytes="):
                is_range_request = True
                range_value = range_header[len("bytes=") :]
                if "-" in range_value:
                    begin_str, end_str = range_value.split("-", 1)
                    if begin_str:
                        begin = int(begin_str.strip())
                    if end_str:
                        end = int(end_str.strip())
                else:
                    begin = int(range_value)

        if member := await get_member(path):
            if isinstance(member, Resource):
                content, media_type, last_modified, content_length = (
                    await asyncio.gather(
                        member.get_content(begin, end),
                        member.content_type(),
                        member.last_modified(),
                        member.content_length(),
                    )
                )

                headers = {
                    "Last-Modified": str(last_modified),
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(
                        content_length
                        if not is_range_request
                        else calc_content_length(content_length, begin, end)
                    ),
                    "Content-Disposition": f'attachment; filename="{path.split("/")[-1]}"',
                }

                if is_range_request:
                    actual_end = end if end != -1 else content_length - 1
                    headers["Content-Range"] = (
                        f"bytes {begin}-{actual_end}/{content_length}"
                    )
                    status_code = HTTPStatus.PARTIAL_CONTENT
                else:
                    status_code = HTTPStatus.OK

                return StreamingResponse(
                    content=content,
                    status_code=status_code,
                    media_type=media_type,
                    headers=headers,
                )

            raise ValueError("Expected a Resource, got a Folder")

        raise NOT_FOUND

    @app.put("/{path:path}")
    async def put(request: Request, path: str):
        content_length = request.headers.get("Content-Length", "0")
        size = int(content_length)
        if not (member := await get_member(path)):
            member = await (await root()).create_empty_resource(path)
        if isinstance(member, Resource):
            if size > 0:
                await member.overwrite(request.stream(), size=size)
            return CREATED
        raise CONFLICT("Cannot PUT to a directory")

    @app.delete("/{path:path}")
    async def delete(request: Request, path: str):
        if member := await get_member(path):
            await member.remove()
            return NO_CONTENT
        raise NOT_FOUND

    @app.api_route("/{path:path}", methods=["MKCOL"])
    async def mkcol(request: Request, path: str):
        parent_path, folder_name = split_path(path)
        if parent := await get_member(parent_path):
            if not isinstance(parent, Folder):
                raise CONFLICT(f"Parent {parent_path} is not a folder.")
            if member := await parent.member(folder_name):
                if isinstance(member, Folder):
                    return CREATED
                raise CONFLICT(f"Resource {path} is a file.")
            await parent.create_folder(folder_name)
            return CREATED
        raise CONFLICT(f"Parent folder {parent_path} does not exist.")

    @app.api_route("/{path:path}", methods=["COPY"])
    async def copy(request: Request, path: str):
        destination = request.headers.get("Destination")
        if not destination:
            raise BAD_REQUEST("Destination header is required for COPY.")
        if member := await get_member(path):
            dest_path = extract_path_from_destination(destination)
            await member.copy_to(dest_path)
            return CREATED
        raise NOT_FOUND

    @app.api_route("/{path:path}", methods=["MOVE"])
    async def move(request: Request, path: str):
        destination = request.headers.get("Destination")
        if not destination:
            raise BAD_REQUEST("Destination header is required for MOVE.")
        if member := await get_member(path):
            dest_path = extract_path_from_destination(destination)
            await member.move_to(dest_path)
            return CREATED
        raise NOT_FOUND

    @app.api_route("/{full_path:path}", methods=["LOCK"])
    async def lock_handler(full_path: str):
        return Response(
            status_code=200,
            headers={
                "Content-Type": "application/xml",
                "Lock-Token": f"<{LOCK_TOKEN}>",
            },
            content=f"""
            <D:prop xmlns:D="DAV:">
                <D:lockdiscovery>
                    <D:activelock>
                        <D:locktype><D:write/></D:locktype>
                        <D:lockscope><D:exclusive/></D:lockscope>
                        <D:depth>Infinity</D:depth>
                        <D:owner><D:href>/</D:href></D:owner>
                        <D:timeout>Second-3600</D:timeout>
                        <D:locktoken><D:href>{LOCK_TOKEN}</D:href></D:locktoken>
                    </D:activelock>
                </D:lockdiscovery>
            </D:prop>
            """.strip(),
        )

    @app.api_route("/{full_path:path}", methods=["UNLOCK"])
    async def unlock_handler(full_path: str):
        return Response(status_code=204)

    return app
