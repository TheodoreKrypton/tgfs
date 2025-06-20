from typing import Optional, Callable, Any

from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from contextvars import ContextVar
import uuid

from starlette.responses import StreamingResponse

from asgidav.folder import Folder
from asgidav.resource import Resource
from .reqres import PropfindRequest, propfind


class RootFolder:
    __root_folder: Optional[Folder] = None

    @classmethod
    def set(cls, folder: Folder):
        cls.__root_folder = folder

    @classmethod
    def get(cls) -> Folder:
        if cls.__root_folder is None:
            raise ValueError("Root folder is not set.")
        return cls.__root_folder


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
async def add_uuid_middleware(request: Request, call_next: Callable[[Any], Any]) -> Any:
    # Set request UUID.
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
    if member := await RootFolder.get().member(path):
        resp = await propfind((member,), r.depth, r.props)
        return Response(
            resp,
            media_type="application/xml",
        )

    return Response(status_code=404)


@app.head("/{path:path}")
async def head(request: Request, path: str):
    if member := await RootFolder.get().member(path):
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

    if member := await RootFolder.get().member(path):
        if isinstance(member, Resource):
            return StreamingResponse(
                content=await member.get_content(begin, end),
                media_type=await member.content_type(),
                headers={
                    "Last-Modified": str(await member.last_modified()),
                },
            )
        else:
            raise ValueError("Expected a Resource, got a Folder")
    return Response(status_code=404)


@app.put("/{path:path}")
async def put(request: Request, path: str):
    if not (member := await RootFolder.get().member(path)):
        member = await RootFolder.get().create_empty_resource(path)
    if isinstance(member, Resource):
        await member.write(
            request.stream(), size=int(request.headers.get("Content-Length", 0))
        )
        return Response(
            status_code=201,
            headers={
                "Location": f"/{path}",
            },
        )
    return Response(
        status_code=405,
        headers={
            "Allow": "GET, HEAD, POST, PUT, DELETE, TRACE, OPTIONS, PROPFIND, PROPPATCH, COPY, MOVE, LOCK, UNLOCK, MKCOL",
        },
    )
