import json
from typing import AsyncIterator, Optional

from tgfs.core.api import MessageApi
from tgfs.core.model import TGFSFileVersion, TGFSMetadata
from tgfs.core.repository.interface import IFileContentRepository, IMetaDataRepository
from tgfs.errors import MetadataNotFound, MetadataNotInitialized
from tgfs.reqres import FileMessageFromBuffer, SentFileMessage


class TGMsgMetadataRepository(IMetaDataRepository):
    METADATA_FILE_NAME = "metadata.json"

    def __init__(self, message_api: MessageApi, fc_repo: IFileContentRepository):
        super().__init__()

        self.__message_api = message_api
        self.__fc_repo = fc_repo

        self.__message_id: Optional[int] = None

    async def push(self) -> None:
        if not self.metadata:
            raise MetadataNotInitialized()

        buffer = json.dumps(self.metadata.to_dict()).encode()
        if self.__message_id is not None:
            await self.__fc_repo.update(
                self.__message_id,
                buffer,
                self.METADATA_FILE_NAME,
            )
        else:
            resp = await self.__fc_repo.save(
                FileMessageFromBuffer.new(
                    name=self.METADATA_FILE_NAME,
                    buffer=buffer,
                )
            )
            message_id = resp[0].message_id
            await self.__message_api.pin_message(message_id=message_id)
            self.__message_id = message_id

    @staticmethod
    async def __read_all(async_iter: AsyncIterator[bytes]) -> bytes:
        result = bytearray()
        async for chunk in async_iter:
            result.extend(chunk)
        return bytes(result)

    async def get(self) -> TGFSMetadata:
        pinned_message = await self.__message_api.get_pinned_message()
        if not pinned_message or not pinned_message.document:
            raise MetadataNotFound()

        temp_fv = TGFSFileVersion.from_sent_file_message(
            SentFileMessage(pinned_message.message_id, pinned_message.document.size)
        )

        metadata = TGFSMetadata.from_dict(
            json.loads(
                await self.__read_all(
                    await self.__fc_repo.get(
                        temp_fv,
                        begin=0,
                        end=-1,
                        name=self.METADATA_FILE_NAME,
                    )
                )
            )
        )

        self.__message_id = pinned_message.message_id
        return metadata
