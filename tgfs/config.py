import os
from dataclasses import dataclass

import yaml
from telethon.tl.types import PeerChannel


@dataclass
class WebDAVConfig:
    host: str
    port: int
    path: str

    @classmethod
    def from_dict(cls, data: dict) -> "WebDAVConfig":
        return cls(host=data["host"], port=data["port"], path=data["path"])


@dataclass
class DownloadConfig:
    chunk_size_kb: int

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadConfig":
        return cls(chunk_size_kb=data["chunk_size_kb"])


@dataclass
class UserConfig:
    password: str

    @classmethod
    def from_dict(cls, data: dict) -> "UserConfig":
        return cls(password=data["password"])


@dataclass
class TGFSConfig:
    users: dict[str, UserConfig]
    download: DownloadConfig

    @classmethod
    def from_dict(cls, data: dict) -> "TGFSConfig":
        return cls(
            users={
                username: UserConfig.from_dict(user)
                for username, user in data["users"].items()
            },
            download=DownloadConfig(**data["download"]),
        )


@dataclass
class BotConfig:
    token: str
    session_file: str

    @classmethod
    def from_dict(cls, data: dict) -> "BotConfig":
        return cls(
            token=data["token"], session_file=os.path.expanduser(data["session_file"])
        )


@dataclass
class AccountConfig:
    session_file: str

    @classmethod
    def from_dict(cls, data: dict) -> "AccountConfig":
        return cls(session_file=os.path.expanduser(data["session_file"]))


@dataclass
class TelegramConfig:
    api_id: int
    api_hash: str
    account: AccountConfig
    bot: BotConfig
    private_file_channel: PeerChannel

    @classmethod
    def from_dict(cls, data: dict) -> "TelegramConfig":
        return cls(
            api_id=data["api_id"],
            api_hash=data["api_hash"],
            account=AccountConfig.from_dict(data["account"]),
            bot=BotConfig.from_dict(data["bot"]),
            private_file_channel=PeerChannel(int(data["private_file_channel"])),
        )


@dataclass
class Config:
    telegram: TelegramConfig
    tgfs: TGFSConfig
    webdav: WebDAVConfig

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        return cls(
            telegram=TelegramConfig.from_dict(data["telegram"]),
            tgfs=TGFSConfig.from_dict(data["tgfs"]),
            webdav=WebDAVConfig.from_dict(data["webdav"]),
        )


__config_file_path = ""
__config: Config | None = None


def set_config_file(file_path: str) -> None:
    global __config_file_path
    __config_file_path = file_path


def __load_config(file_path: str) -> "Config":
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
        return Config.from_dict(data)


def get_config() -> "Config":
    global __config
    if __config is None:
        __config = __load_config(__config_file_path)
    return __config
