from typing import Optional

from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware

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
            return await propfind((member,), r.depth, r.props)
        pass
    return Response(status_code=404)
