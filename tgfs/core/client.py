from typing import List

from telethon import TelegramClient

from tgfs.core.api import DirectoryApi, FileApi, FileDescApi, MessageApi, MetaDataApi
from tgfs.core.repository.interface import (
    IMetaDataRepository,
)
from tgfs.core.repository.impl import (
    TGMsgFileContentRepository,
    TGMsgFDRepository,
    TGMsgMetadataRepository,
    GithubRepoMetadataRepository,
)
from tgfs.config import get_config, MetadataType
from tgfs.telegram.impl.telethon import TelethonAPI
from tgfs.telegram.interface import TDLibApi


config = get_config()


class Client:
    def __init__(self, file_api: FileApi, dir_api: DirectoryApi):
        self.file_api = file_api
        self.dir_api = dir_api

    @classmethod
    async def create(
        cls,
        account: TelegramClient,
        bots: List[TelegramClient],
    ) -> "Client":
        message_api = MessageApi(
            TDLibApi(
                account=TelethonAPI(account), bots=[TelethonAPI(bot) for bot in bots]
            )
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
                    f"configuration tgfs -> metadata -> github is required."
                )
            metadata_repo = GithubRepoMetadataRepository(github_repo_config)

        fd_api = FileDescApi(fd_repo, fc_repo)

        metadata_api = MetaDataApi(metadata_repo)
        await metadata_api.init()

        file_api = FileApi(metadata_api, fd_api)
        dir_api = DirectoryApi(metadata_api)

        return cls(file_api=file_api, dir_api=dir_api)
