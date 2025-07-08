from typing import Optional

from asgidav.app import create_app
from tgfs.api import Client

from .cache import Member, RootCache
from .folder import Folder


async def _get_member(path: str, client: Client) -> Optional[Member]:
    path = path if path.startswith("/") else f"/{path}"
    if res := RootCache.get(path):
        return res
    root = Folder("/", client)
    if res := await root.member(path.lstrip("/")):
        RootCache.set(path, res)
        return res
    return None


def create_webdav_app(client):
    return create_app(lambda path: _get_member(path, client))
