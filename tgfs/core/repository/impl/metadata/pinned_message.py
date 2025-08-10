import json
from typing import AsyncIterator, Optional

from tgfs.core.api import MessageApi
from tgfs.core.model import TGFSDirectory, TGFSFileVersion, TGFSMetadata
from tgfs.core.repository.interface import IFileContentRepository, IMetaDataRepository
from tgfs.errors import (
    MetadataNotInitialized,
    NoPinnedMessage,
)
from tgfs.reqres import (
    FileMessageFromBuffer,
    MessageRespWithDocument,
    SentFileMessage,
)


class TGMsgMetadataRepository(IMetaDataRepository):
    METADATA_FILE_NAME = "metadata.json"

    def __init__(self, message_api: MessageApi, fc_repo: IFileContentRepository):
        super().__init__()

        self._message_api = message_api
        self._fc_repo = fc_repo

        self._message_id: Optional[int] = None

    async def push(self) -> None:
        if not self.metadata:
            raise MetadataNotInitialized()

        buffer = json.dumps(self.metadata.to_dict()).encode()
        if self._message_id is not None:
            await self._fc_repo.update(
                self._message_id,
                buffer,
                self.METADATA_FILE_NAME,
            )
        else:
            resp = await self._fc_repo.save(
                FileMessageFromBuffer.new(
                    name=self.METADATA_FILE_NAME,
                    buffer=buffer,
                )
            )
            message_id = resp[0].message_id
            await self._message_api.pin_message(message_id=message_id)
            self._message_id = message_id

    @staticmethod
    async def _read_all(async_iter: AsyncIterator[bytes]) -> bytes:
        result = bytearray()
        async for chunk in async_iter:
            result.extend(chunk)
        return bytes(result)

    async def new_metadata(self) -> MessageRespWithDocument:
        root = TGFSDirectory.root_dir()
        self.metadata = TGFSMetadata(root)
        self._message_id = None
        await self.push()
        return await self._message_api.get_pinned_message()

    async def get(self) -> TGFSMetadata:
        try:
            pinned_message = await self._message_api.get_pinned_message()
        except NoPinnedMessage:
            pinned_message = await self.new_metadata()

        temp_fv = TGFSFileVersion.from_sent_file_message(
            SentFileMessage(pinned_message.message_id, pinned_message.document.size)
        )

        metadata = TGFSMetadata.from_dict(
            json.loads(
                await self._read_all(
                    await self._fc_repo.get(
                        temp_fv,
                        begin=0,
                        end=-1,
                        name=self.METADATA_FILE_NAME,
                    )
                )
            )
        )

        self._message_id = pinned_message.message_id
        return metadata
