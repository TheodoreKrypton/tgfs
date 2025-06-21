from telethon import TelegramClient

from tgfs.api.client.repository import (
    FileRepository,
    TGMsgFDRepository,
    TGMsgMetadataRepository,
)
from tgfs.api.impl.telethon import TelethonAPI
from tgfs.api.interface import TDLibApi

from .directory import DirectoryApi
from .file import FileApi
from .file_desc import FileDescApi
from .message import MessageApi
from .metadata import MetaDataApi


class Client:
    def __init__(self, file_api: FileApi, dir_api: DirectoryApi):
        self.file_api = file_api
        self.dir_api = dir_api

    @classmethod
    async def create(
        cls,
        account: TelegramClient,
        bot: TelegramClient,
    ) -> "Client":
        message_api = MessageApi(
            TDLibApi(account=TelethonAPI(account), bot=TelethonAPI(bot))
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
