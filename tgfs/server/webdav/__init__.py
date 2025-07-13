from typing import Optional

from asgidav.app import create_app
from tgfs.api import Client

from .cache import Member, fs_cache
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


def create_webdav_app(client):
    fs_cache.set("/", Folder("/", client))
    return create_app(lambda path: _get_member(path, client))
