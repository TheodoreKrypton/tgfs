from typing import List

from telethon import TelegramClient

from tgfs.core.api import DirectoryApi, FileApi, FileDescApi, MessageApi, MetaDataApi
from tgfs.core.repository import (
    FileRepository,
    TGMsgFDRepository,
    TGMsgMetadataRepository,
)

from tgfs.telegram.impl.telethon import TelethonAPI
from tgfs.telegram.interface import TDLibApi


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
        file_repo = FileRepository(message_api)
        fd_repo = TGMsgFDRepository(message_api)
        metadata_repo = TGMsgMetadataRepository(message_api, file_repo)

        fd_api = FileDescApi(fd_repo, file_repo)

        metadata_api = MetaDataApi(metadata_repo)
        await metadata_api.init()

        file_api = FileApi(metadata_api, fd_api)
        dir_api = DirectoryApi(metadata_api)

        return cls(file_api=file_api, dir_api=dir_api)
