import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Literal, Optional, Self, TypedDict

import yaml

logger = logging.getLogger(__name__)

DATA_DIR = os.environ.get("TGFS_DATA_DIR", os.path.expanduser("~/.tgfs"))
CONFIG_FILE = os.environ.get("TGFS_CONFIG_FILE", "config.yaml")


@dataclass
class WebDAVConfig:
    host: str
    port: int
    path: str

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(host=data["host"], port=data["port"], path=data["path"])


@dataclass
class ManagerConfig:
    host: str
    port: int

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(host=data["host"], port=data["port"])


@dataclass
class DownloadConfig:
    chunk_size_kb: int

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(chunk_size_kb=data["chunk_size_kb"])


@dataclass
class UserConfig:
    password: str
    readonly: bool

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(password=data["password"], readonly=data.get("readonly", False))


@dataclass
class JWTConfig:
    secret: str
    algorithm: str
    life: int

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            secret=data["secret"], algorithm=data["algorithm"], life=data["life"]
        )


@dataclass
class GithubRepoConfig:
    repo: str
    commit: str
    access_token: str

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            repo=data["repo"],
            commit=data["commit"],
            access_token=data["access_token"],
        )


class MetadataType(Enum):
    PINNED_MESSAGE = "pinned_message"
    GITHUB_REPO = "github_repo"


class MetadataConfigDict(TypedDict):
    name: str
    type: str
    github_repo: Optional[Dict]


@dataclass
class MetadataConfig:
    name: str
    type: MetadataType
    github_repo: Optional[GithubRepoConfig]

    @classmethod
    def from_dict(cls, data: MetadataConfigDict) -> Self:
        if (
            data.get("type", MetadataType.PINNED_MESSAGE.value)
            == MetadataType.PINNED_MESSAGE.value
        ):
            return cls(
                name=data.get("name", "default"),
                type=MetadataType.PINNED_MESSAGE,
                github_repo=None,
            )
        if data["type"] == MetadataType.GITHUB_REPO.value:
            if not (gh_repo_config := data.get("github_repo")):
                raise ValueError(
                    "GitHub repo configuration is required for GITHUB_REPO type"
                )
            return cls(
                name=data.get("name", "default"),
                type=MetadataType.GITHUB_REPO,
                github_repo=GithubRepoConfig.from_dict(gh_repo_config),
            )
        raise ValueError(
            f"Unknown metadata type: {data['type']}, available options: {', '.join(e.value for e in MetadataType)}"
        )


@dataclass
class ServerConfig:
    host: str
    port: int

    @classmethod
    def from_dict(cls, data: Dict) -> "ServerConfig":
        return cls(host=data["host"], port=data["port"])


@dataclass
class TGFSConfig:
    users: dict[str, UserConfig]
    download: DownloadConfig
    jwt: JWTConfig
    metadata: Dict[str, MetadataConfig]
    server: ServerConfig

    @classmethod
    def from_dict(cls, data: Dict) -> Self:
        metadata_config: Dict[str, MetadataConfigDict] = data.get("metadata", {})

        return cls(
            users=(
                {
                    username: UserConfig.from_dict(user)
                    for username, user in data["users"].items()
                }
                if data["users"]
                else {}
            ),
            download=DownloadConfig.from_dict(data["download"]),
            jwt=JWTConfig.from_dict(data["jwt"]),
            metadata={
                k: MetadataConfig.from_dict(v) for k, v in metadata_config.items()
            },
            server=ServerConfig.from_dict(data["server"]),
        )


def expand_path(path: str) -> str:
    return os.path.expanduser(os.path.join(DATA_DIR, path)).replace("/", os.path.sep)


@dataclass
class BotConfig:
    token: str
    session_file: str
    tokens: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "BotConfig":
        return cls(
            token=data.get("token", ""),
            tokens=data.get("tokens", []),
            session_file=expand_path(data["session_file"]),
        )


@dataclass
class AccountConfig:
    session_file: str
    used_to_upload: bool

    @classmethod
    def from_dict(cls, data: dict) -> "AccountConfig":
        return cls(
            session_file=expand_path(data["session_file"]),
            used_to_upload=data.get("used_to_upload", False),
        )


@dataclass
class TelegramConfig:
    api_id: int
    api_hash: str
    account: Optional[AccountConfig]
    bot: BotConfig
    private_file_channel: List[str]
    lib: Literal["pyrogram", "telethon"]

    @classmethod
    def from_dict(cls, data: dict) -> "TelegramConfig":
        return cls(
            api_id=data["api_id"],
            api_hash=data["api_hash"],
            account=(
                AccountConfig.from_dict(data["account"]) if "account" in data else None
            ),
            bot=BotConfig.from_dict(data["bot"]),
            private_file_channel=data["private_file_channel"],
            lib=data.get("lib") or "telethon",
        )


@dataclass
class Config:
    telegram: TelegramConfig
    tgfs: TGFSConfig

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        return cls(
            telegram=TelegramConfig.from_dict(data["telegram"]),
            tgfs=TGFSConfig.from_dict(data["tgfs"]),
        )


__config_file_path = expand_path(os.path.join(DATA_DIR, CONFIG_FILE))
__config: Config | None = None


def _load_config(file_path: str) -> Config:
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
        return Config.from_dict(data)


def get_config() -> Config:
    global __config
    if __config is None:
        logger.info(f"Using configuration file: {__config_file_path}")
        __config = _load_config(__config_file_path)
    return __config
