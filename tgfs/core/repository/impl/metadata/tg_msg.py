import json
from typing import AsyncIterator

from tgfs.reqres import FileMessageFromBuffer, FileTags
from tgfs.errors import MetadataNotFound
from tgfs.core.api import MessageApi
from tgfs.core.model import TGFSMetadata
from tgfs.core.repository.impl.file import FileRepository
from tgfs.core.repository.interface import IMetaDataRepository


class TGMsgMetadataRepository(IMetaDataRepository):
    METADATA_FILE_NAME = "metadata.json"

    def __init__(self, message_api: MessageApi, file_repo: FileRepository):
        self.__message_api = message_api
        self.__file_repo = file_repo

    async def save(self, metadata: TGFSMetadata) -> int:
        buffer = json.dumps(metadata.to_dict()).encode()
        if metadata.message_id:
            return await self.__file_repo.update(
                metadata.message_id,
                buffer,
                self.METADATA_FILE_NAME,
            )
        resp = await self.__file_repo.save(
            FileMessageFromBuffer(
                name=self.METADATA_FILE_NAME,
                caption="",
                tags=FileTags(),
                buffer=buffer,
            )
        )
        await self.__message_api.pin_message(message_id=resp.message_id)
        return resp.message_id

    @staticmethod
    async def __read_all(async_iter: AsyncIterator[bytes]) -> bytes:
        result = bytearray()
        async for chunk in async_iter:
            result.extend(chunk)
        return bytes(result)

    async def get(self) -> TGFSMetadata:
        pinned_message = await self.__message_api.get_pinned_message()
        if not pinned_message:
            raise MetadataNotFound()

        metadata = TGFSMetadata.from_dict(
            json.loads(
                await self.__read_all(
                    await self.__file_repo.download_file(
                        self.METADATA_FILE_NAME,
                        pinned_message.message_id,
                        begin=0,
                        end=-1,
                    )
                )
            )
        )

        metadata.message_id = pinned_message.message_id
        return metadata
