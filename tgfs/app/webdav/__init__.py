from typing import Optional

from asgidav.app import User, create_app, default_auth_callback
from tgfs.core import Client

from ...config import Config
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


def create_webdav_app(client, config: Config):
    fs_cache.set("/", Folder("/", client))

    def authenticate(username: str, password: str) -> Optional[User]:
        if (user := config.tgfs.users.get(username)) and user.password == password:
            return User(
                username=username, permission="readonly" if user.readonly else "admin"
            )
        return None

    return create_app(
        get_member=lambda path: _get_member(path, client),
        jwt_config={
            "secret": config.tgfs.jwt.secret,
            "algorithm": config.tgfs.jwt.algorithm,
            "life": config.tgfs.jwt.life,
        },
        auth_callback=authenticate if config.tgfs.users else default_auth_callback,
    )
