from tgfs.config import get_config
from tgfs.errors.tgfs import LoginFailed

from .user import AdminUser, ReadonlyUser, User

config = get_config()


def authenticate(username: str, password: str) -> User:
    if not config.tgfs.users:
        return ReadonlyUser("anonymous")
    if not username:
        raise LoginFailed("Anonymous login is disabled.")
    if (user := config.tgfs.users.get(username)) and user.password == password:
        return AdminUser(username) if not user.readonly else ReadonlyUser(username)
    raise LoginFailed(f"No such user ({username}) or password is incorrect.")
