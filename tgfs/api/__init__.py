from .client.api.client import Client
from .impl.telethon import login_as_account, login_as_bots
from .ops import Ops

__all__ = [
    "Ops",
    "Client",
    "login_as_bots",
    "login_as_account",
]
