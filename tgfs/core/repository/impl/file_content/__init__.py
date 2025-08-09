import asyncio
import logging
from typing import Generator, List

from tgfs.core.api import MessageApi
from tgfs.core.model import EMPTY_FILE_MESSAGE, TGFSFileVersion
from tgfs.core.repository.interface import IFileContentRepository
from tgfs.errors import TechnicalError
from tgfs.reqres import (
    EditMessageMediaReq,
    FileContent,
    FileMessage,
    FileMessageFromBuffer,
    FileMessageFromPath,
    SentFileMessage,
    UploadableFileMessage,
)
from tgfs.utils.chained_async_iterator import ChainedAsyncIterator

from .file_uploader import create_uploader

logger = logging.getLogger(__name__)


class TGMsgFileContentRepository(IFileContentRepository):
    def __init__(self, message_api: MessageApi):
        self.__message_api = message_api

    @staticmethod
    def __get_file_caption(
        file_msg: FileMessage,
    ) -> str:
        if not isinstance(file_msg, UploadableFileMessage):
            return ""
        return file_msg.caption

    async def __send_file(self, file_msg: UploadableFileMessage) -> SentFileMessage:
        message_id: int = EMPTY_FILE_MESSAGE

        async def on_complete():
            nonlocal message_id
            message_id = (
                await uploader.send(
                    self.__message_api.private_file_channel,
                    self.__get_file_caption(file_msg),
                )
            ).message_id

        uploader = create_uploader(self.__message_api.tdlib, file_msg, on_complete)
        size = await uploader.upload(file_msg, file_msg.name)

        return SentFileMessage(message_id=message_id, size=size)

    @staticmethod
    def _size_for_parts(size: int) -> Generator[int]:
        part_size = 1024 * 1024 * 1024  # 1 GB

        parts = (size + part_size - 1) // part_size
        for i in range(parts - 1):
            yield part_size
        yield size - (parts - 1) * part_size

    async def save(self, file_msg: UploadableFileMessage) -> List[SentFileMessage]:
        size = file_msg.get_size()

        res: List[SentFileMessage] = []
        file_name = file_msg.name or "unnamed"

        for i, part_size in enumerate(self._size_for_parts(size)):
            file_msg.name = f"{file_name}.part{i + 1}"
            file_msg.size = part_size
            res.append(await self.__send_file(file_msg))

            logger.info(f"Saving {file_msg.name}")
            if isinstance(file_msg, FileMessageFromBuffer | FileMessageFromPath):
                file_msg.offset += part_size

        return res

    async def update(self, message_id: int, buffer: bytes, name: str) -> int:
        file_msg: FileMessageFromBuffer = FileMessageFromBuffer.new(
            buffer=buffer,
            name=name,
        )

        async def on_complete():
            await uploader.client.edit_message_media(
                EditMessageMediaReq(
                    chat=self.__message_api.private_file_channel,
                    message_id=message_id,
                    file=uploader.get_uploaded_file(),
                )
            )

        uploader = create_uploader(self.__message_api.tdlib, file_msg, on_complete)
        await uploader.upload(file_msg, file_msg.name)
        return message_id

    @staticmethod
    def __get_file_part_to_download(
        fv: TGFSFileVersion, begin: int, end: int
    ) -> Generator[tuple[int, int, int]]:
        if fv.size <= 0:
            return
        if end < 0:
            end = fv.size
        if begin < 0:
            raise TechnicalError(
                f"Invalid begin value {begin} for file version {fv.id} with size {fv.size}"
            )
        if begin > end:
            raise TechnicalError(
                f"Invalid range: begin {begin} is greater than end {end} for file version {fv.id}"
            )
        if end > fv.size:
            raise TechnicalError(
                f"Invalid end value {end} for file version {fv.id} with size {fv.size}"
            )

        offset = 0
        i_part = 0

        while i_part < len(fv.part_sizes) and offset + fv.part_sizes[i_part] <= begin:
            offset += fv.part_sizes[i_part]
            i_part += 1

        if i_part >= len(fv.part_sizes):
            raise TechnicalError(
                f"Begin offset {begin} exceeds total file size {fv.size} for file version {fv.id}"
            )

        while i_part < len(fv.part_sizes) and offset < end:
            part_size = fv.part_sizes[i_part]
            part_begin = max(0, begin - offset)
            part_end = min(part_size, end - offset)
            if part_begin < part_end:
                yield fv.message_ids[i_part], part_begin, part_end
            offset += part_size
            i_part += 1

    async def get(
        self, fv: TGFSFileVersion, begin: int, end: int, name: str
    ) -> FileContent:
        logger.info(f"Retrieving file content for {name}@{fv.id} from {begin} to {end}")

        tasks = []
        for message_id, begin, end in self.__get_file_part_to_download(fv, begin, end):
            tasks.append(self.__message_api.download_file(message_id, begin, end))

        return ChainedAsyncIterator((x.chunks for x in await asyncio.gather(*tasks)))
