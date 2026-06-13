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
class EncryptionConfig:
    """Optional at-rest encryption settings.

    ``passphrase_env`` / ``passphrase`` / ``passphrase_file`` are mutually
    exclusive; the loader picks the first one that is set. A file containing
    the passphrase is the recommended option for systemd deployments (pair
    it with a ``LoadCredential=`` unit directive).

    ``master_salt_file`` stores the 16-byte master salt produced on the
    very first run. Back this up alongside your TGFS metadata -- without it
    the master key cannot be re-derived even with the correct passphrase.
    """

    enabled: bool
    passphrase: Optional[str]
    passphrase_env: Optional[str]
    passphrase_file: Optional[str]
    master_salt_file: str
    chunk_size: int

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "EncryptionConfig":
        if not data:
            return cls(
                enabled=False,
                passphrase=None,
                passphrase_env=None,
                passphrase_file=None,
                master_salt_file=expand_path("master.salt"),
                chunk_size=64 * 1024,
            )
        return cls(
            enabled=bool(data.get("enabled", False)),
            passphrase=data.get("passphrase"),
            passphrase_env=data.get("passphrase_env"),
            passphrase_file=(
                expand_path(data["passphrase_file"])
                if data.get("passphrase_file")
                else None
            ),
            master_salt_file=expand_path(
                data.get("master_salt_file", "master.salt")
            ),
            chunk_size=int(data.get("chunk_size", 64 * 1024)),
        )

    def resolve_passphrase(self) -> str:
        """Return the passphrase from whichever source is configured.

        Raises :class:`ValueError` if encryption is enabled but no source
        was configured. Stripping a trailing newline makes the
        ``passphrase_file`` flow forgiving of editors that always add one.
        """
        if self.passphrase_env:
            value = os.environ.get(self.passphrase_env)
            if value is None:
                raise ValueError(
                    f"encryption passphrase env var '{self.passphrase_env}' not set"
                )
            return value
        if self.passphrase_file:
            with open(self.passphrase_file, "r", encoding="utf-8") as fh:
                return fh.read().rstrip("\n")
        if self.passphrase:
            return self.passphrase
        raise ValueError(
            "encryption enabled but no passphrase source configured "
            "(set one of passphrase, passphrase_env, passphrase_file)"
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
    encryption: EncryptionConfig

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
            encryption=EncryptionConfig.from_dict(data.get("encryption")),
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
    used_to_download: bool

    @classmethod
    def from_dict(cls, data: dict) -> "AccountConfig":
        return cls(
            session_file=expand_path(data["session_file"]),
            used_to_upload=data.get("used_to_upload", False),
            used_to_download=data.get("used_to_download", False),
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
