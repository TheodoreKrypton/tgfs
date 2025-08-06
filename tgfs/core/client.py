from typing import List, Optional

import telethon.tl.types as tlt
from telethon import TelegramClient
from telethon.tl.types import PeerChannel

from tgfs.config import MetadataType, get_config
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
    def __init__(self, message_api: MessageApi, file_api: FileApi, dir_api: DirectoryApi):
        self.message_api = message_api
        self.file_api = file_api
        self.dir_api = dir_api

    @classmethod
    async def create(
        cls,
        bots: List[TelegramClient],
        account: Optional[TelegramClient] = None,
    ) -> "Client":
        try:
            private_file_channel = PeerChannel(
                int(config.telegram.private_file_channel)
            )
        except ValueError:
            entity = await bots[0].get_entity(
                f"@{config.telegram.private_file_channel}"
            )
            if not isinstance(entity, tlt.Channel):
                raise TechnicalError("Expected a Telegram channel")
            private_file_channel = PeerChannel(entity.id)

        message_api = MessageApi(
            TDLibApi(
                account=TelethonAPI(account) if account else None,
                bots=[TelethonAPI(bot) for bot in bots],
            ),
            private_file_channel,
        )

        fc_repo = TGMsgFileContentRepository(message_api)
        fd_repo = TGMsgFDRepository(message_api)

        if config.tgfs.metadata.type == MetadataType.PINNED_MESSAGE:
            metadata_repo: IMetaDataRepository = TGMsgMetadataRepository(
                message_api, fc_repo
            )
        else:
            if (github_repo_config := config.tgfs.metadata.github_repo) is None:
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

        return cls(message_api=message_api, file_api=file_api, dir_api=dir_api)
