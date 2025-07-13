import asyncio
import uuid
from collections.abc import Awaitable
from contextvars import ContextVar
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from .folder import Folder
from .member import Member
from .reqres import PropfindRequest, propfind
from .resource import Resource

NO_CONTENT = Response(status_code=204)
CREATED = Response(status_code=201)
NOT_FOUND = Response(status_code=404)
CONFLICT = Response(status_code=409)


def split_path(path: str) -> tuple[str, str]:
    path = path.strip("/")
    parts = path.rsplit("/", 1)
    if len(parts) == 1:
        return "/", parts[0]
    return parts[0], parts[1]


def create_app(get_member: Callable[[str], Awaitable[Optional[Member]]]) -> FastAPI:
    async def root() -> Folder:
        res = await get_member("/")
        if not res or not isinstance(res, Folder):
            raise ValueError("/ is not a Folder")
        return res

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust this to your needs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uuid_context = ContextVar("uuid", default="")

    @app.middleware("http")
    async def add_uuid_middleware(
        request: Request, call_next: Callable[[Any], Any]
    ) -> Any:
        uuid_context.set(str(uuid.uuid4()))
        return await call_next(request)

    @app.options("/{path:path}")
    async def options():
        return Response(
            status_code=200,
            headers={
                "Allow": "GET, HEAD, POST, PUT, DELETE, TRACE, OPTIONS, PROPFIND, PROPPATCH, COPY, MOVE, LOCK, UNLOCK, MKCOL",
                "Content-Length": "0",
                "DAV": "1",
                "MS-Author-Via": "DAV",
            },
        )

    @app.api_route("/{path:path}", methods=["PROPFIND"])
    async def handle_propfind(request: Request, path: str):
        r = await PropfindRequest.from_request(request)
        if member := await get_member(path):
            resp = await propfind((member,), r.depth, r.props)
            return Response(
                resp,
                media_type="application/xml",
            )

        return Response(status_code=404)

    @app.head("/{path:path}")
    async def head(request: Request, path: str):
        if member := await get_member(path):
            if isinstance(member, Folder):
                return Response(
                    status_code=200,
                    headers={
                        "Content-Type": "httpd/unix-directory",
                        "Last-Modified": str(await member.last_modified()),
                    },
                )
            return Response(
                status_code=200,
                headers={
                    "Content-Type": await member.content_type(),
                    "Last-Modified": str(await member.last_modified()),
                },
            )

        return Response(status_code=404)

    @app.get("/{path:path}")
    async def get(request: Request, path: str):
        begin, end = 0, -1
        if "Range" in request.headers:
            range_header = request.headers["Range"]
            if range_header.startswith("bytes="):
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
                content, media_type, last_modified = await asyncio.gather(
                    member.get_content(begin, end),
                    member.content_type(),
                    member.last_modified(),
                )
                return StreamingResponse(
                    content=content,
                    media_type=media_type,
                    headers={
                        "Last-Modified": str(last_modified),
                    },
                )
            raise ValueError("Expected a Resource, got a Folder")
        return Response(status_code=404)

    @app.put("/{path:path}")
    async def put(request: Request, path: str):
        if not (member := await get_member(path)):
            member = await (await root()).create_empty_resource(path)

        size = int(request.headers["Content-Length"])

        if isinstance(member, Resource) and size > 0:
            await member.overwrite(request.stream(), size=size)

        return CREATED

    @app.delete("/{path:path}")
    async def delete(request: Request, path: str):
        if member := await get_member(path):
            await member.remove()
            return NO_CONTENT
        return NOT_FOUND

    @app.api_route("/{path:path}", methods=["MKCOL"])
    async def mkcol(request: Request, path: str):
        parent_path, folder_name = split_path(path)
        if parent := await get_member(parent_path):
            if not isinstance(parent, Folder):
                return Response(
                    status_code=409,
                    content=f"Parent {parent_path} is not a folder.",
                )
            if member := await parent.member(folder_name):
                return (
                    CREATED
                    if isinstance(member, Folder)
                    else Response(
                        status_code=409,
                        content=f"Resource {path} is a file.",
                    )
                )
            await parent.create_folder(folder_name)
            return CREATED
        else:
            return Response(
                status_code=409,
                content=f"Parent folder {parent_path} does not exist.",
            )

    return app
