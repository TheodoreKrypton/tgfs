from typing import List, Optional, Dict

import telethon.tl.types as tlt
from telethon import TelegramClient
from telethon.tl.types import PeerChannel

from tgfs.config import MetadataType, get_config, MetadataConfig
from tgfs.core.api import DirectoryApi, FileApi, FileDescApi, MessageApi, MetaDataApi
from tgfs.core.repository.impl import (
    TGMsgFDRepository,
    TGMsgFileContentRepository,
    TGMsgMetadataRepository,
)
from tgfs.core.repository.interface import (
    IMetaDataRepository,
)
from tgfs.errors import TechnicalError
from tgfs.telegram.impl.telethon import TelethonAPI
from tgfs.telegram.interface import TDLibApi

config = get_config()


class Client:
    def __init__(
        self,
        name: str,
        message_api: MessageApi,
        file_api: FileApi,
        dir_api: DirectoryApi,
    ):
        self.name = name
        self.message_api = message_api
        self.file_api = file_api
        self.dir_api = dir_api

    @classmethod
    async def get_peer_channel(cls, channel_id: str, bot: TelegramClient):
        try:
            return PeerChannel(int(channel_id))
        except ValueError:
            entity = await bot.get_entity(f"@{channel_id}")
            if not isinstance(entity, tlt.Channel):
                raise TechnicalError("Expected a Telegram channel")
            return PeerChannel(entity.id)

    @classmethod
    async def create(
        cls,
        channel_id: str,
        metadata_cfg: MetadataConfig,
        bots: List[TelegramClient],
        account: Optional[TelegramClient] = None,
    ) -> "Client":
        channel = await cls.get_peer_channel(channel_id, bots[0])
        message_api = MessageApi(
            TDLibApi(
                account=TelethonAPI(account) if account else None,
                bots=[TelethonAPI(bot) for bot in bots],
            ),
            channel,
        )

        fc_repo = TGMsgFileContentRepository(message_api)
        fd_repo = TGMsgFDRepository(message_api)

        if metadata_cfg.type == MetadataType.PINNED_MESSAGE:
            metadata_repo: IMetaDataRepository = TGMsgMetadataRepository(
                message_api, fc_repo
            )
        else:
            if (github_repo_config := metadata_cfg.github_repo) is None:
                raise ValueError(
                    "configuration tgfs -> metadata -> github is required."
                )
            from tgfs.core.repository.impl.metadata.github_repo import (
                GithubRepoMetadataRepository,
            )

            metadata_repo = GithubRepoMetadataRepository(github_repo_config)

        fd_api = FileDescApi(fd_repo, fc_repo)

        metadata_api = MetaDataApi(metadata_repo)
        await metadata_api.init()

        file_api = FileApi(metadata_api, fd_api)
        dir_api = DirectoryApi(metadata_api)

        return cls(
            name=metadata_cfg.name,
            message_api=message_api,
            file_api=file_api,
            dir_api=dir_api,
        )


Clients = Dict[str, Client]
