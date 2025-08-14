from typing import Optional

from asgidav.app import METHODS, create_app
from asgidav.member import Member
from tgfs.core import Clients
from tgfs.app.global_fs_cache import gfc, FSCache
from tgfs.app.utils import split_global_path

from .folder import ReadonlyFolder, Folder


async def _get_member(path: str, clients: Clients) -> Optional[Member]:
    if path == "":
        return ReadonlyFolder("/", list(clients.keys()))

    client_name, sub_path = split_global_path(path)

    root = Folder("/", clients[client_name])

    if res := await root.member(sub_path.lstrip("/")):
        return res
    return None


def create_webdav_app(clients: Clients, base_path: str = ""):
    for name, client in clients.items():
        cache = FSCache()
        cache.set("/", Folder("/", client))
        gfc[name] = cache

    return create_app(
        get_member=lambda path: _get_member(path, clients),
        base_path=base_path,
    )


__all__ = [
    "create_webdav_app",
    "METHODS",
]
