from typing import Optional, Callable, Any

from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from contextvars import ContextVar
import uuid


from asgidav.folder import Folder
from .reqres import PropfindRequest, propfind

root_folder: Optional[Folder] = None


def set_root_folder(folder: Folder):
    global root_folder
    root_folder = folder


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
async def handle_options():
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
    if member := await root_folder.member(path.lstrip("/")):
        if isinstance(member, Folder):
            resp = await propfind((member,), r.depth, r.props)
            return Response(
                resp,
                media_type="application/xml",
            )
    return Response(status_code=404)
