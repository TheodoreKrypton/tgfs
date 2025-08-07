from typing import Optional

from asgidav.app import METHODS, create_app
from tgfs.app.cache import Member, fs_cache
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


def create_webdav_app(client: Client, base_path: str = ""):
    fs_cache.set("/", Folder("/", client))

    return create_app(
        get_member=lambda path: _get_member(path, client),
        base_path=base_path,
    )


__all__ = [
    "create_webdav_app",
    "METHODS",
]