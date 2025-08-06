import base64
from typing import Optional

from asgidav.app import User, create_app
from tgfs.app.cache import Member, fs_cache
from tgfs.auth.basic import authenticate as auth_basic
from tgfs.auth.bearer import authenticate as auth_bearer
from tgfs.auth.bearer import login
from tgfs.config import Config
from tgfs.core import Client

from .folder import Folder


async def _get_member(path: str, client: Client) -> Optional[Member]:
    path = path if path.startswith("/") else f"/{path}"
    if res := fs_cache.get(path):
        return res
    root = Folder("/", client)
    if res := await root.member(path.lstrip("/")):
        fs_cache.set(path, res)
        return res
    return None


def create_webdav_app(client, config: Config):
    fs_cache.set("/", Folder("/", client))

    def auth_callback(auth_header: str) -> User:
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user = auth_bearer(token)
        elif auth_header.startswith("Basic "):
            credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, password = credentials.split(":", 1)
            user = auth_basic(username, password)
        else:
            raise ValueError("Unsupported authentication method")
        return User(
            username=user.username,
            permission="readonly" if user.readonly else "admin",
        )

    return create_app(
        get_member=lambda path: _get_member(path, client),
        login_callback=login,
        auth_callback=auth_callback,
    )
