from .ops import Ops
from .client.api.client import Client
from .impl.telethon import login_as_bot, login_as_account


__all__ = [
    "Ops",
    "Client",
    "login_as_bot",
    "login_as_account",
]