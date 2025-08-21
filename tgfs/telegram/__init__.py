from .impl import pyrogram, telethon
from .interface import ITDLibClient, TDLibApi

PyrogramAPI = pyrogram.PyrogramAPI
TelethonAPI = telethon.TelethonAPI

__all__ = [
    "TDLibApi",
    "ITDLibClient",
    "PyrogramAPI",
    "TelethonAPI",
    "pyrogram",
    "telethon",
]
