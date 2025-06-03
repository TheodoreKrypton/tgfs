import json

from tgfs.api.client.api.message import MessageApi
from tgfs.api.client.api.model import FileMessageFromBuffer, FileTags
from tgfs.api.client.repository.impl.file import FileRepository
from tgfs.api.client.repository.interface import IMetaDataRepository
from tgfs.errors.tgfs import MetadataNotFound
from tgfs.model.metadata import TGFSMetadata


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
        else:
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

    async def get(self) -> TGFSMetadata:
        pinned_message = await self.__message_api.get_pinned_message()
        if not pinned_message:
            raise MetadataNotFound()

        metadata = TGFSMetadata.from_dict(
            json.loads(
                await (
                    await self.__file_repo.download_file(
                        self.METADATA_FILE_NAME, pinned_message.message_id
                    )
                ).get_value()
            )
        )

        metadata.message_id = pinned_message.message_id
        return metadata
