import asyncio
import hashlib
import logging
from typing import Generator, List, Optional

from tgfs.core.api import MessageApi
from tgfs.core.model import EMPTY_FILE_MESSAGE, TGFSFileVersion
from tgfs.core.repository.interface import IFileContentRepository
from tgfs.errors import TechnicalError
from tgfs.reqres import (
    EditMessageMediaReq,
    FileContent,
    FileMessageEmpty,
    FileMessageFromBuffer,
    FileMessageFromPath,
    FileTags,
    GeneralFileMessage,
    SentFileMessage,
)
from tgfs.utils.chained_async_iterator import ChainedAsyncIterator

from .file_uploader import create_uploader

logger = logging.getLogger(__name__)


class TGMsgFileContentRepository(IFileContentRepository):
    def __init__(self, message_api: MessageApi):
        self.__message_api = message_api

    @staticmethod
    async def __sha256(
        file_msg: FileMessageFromPath | FileMessageFromBuffer | FileMessageEmpty,
    ) -> str:
        if isinstance(file_msg, FileMessageEmpty):
            raise TechnicalError("Cannot compute SHA256 for an empty file_content")

        if isinstance(file_msg, FileMessageFromPath):
            sha256 = hashlib.sha256()
            with open(file_msg.path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    sha256.update(chunk)
            return sha256.hexdigest()

        if isinstance(file_msg, FileMessageFromBuffer):
            sha256 = hashlib.sha256(file_msg.buffer)
            return sha256.hexdigest()

        raise TechnicalError(
            "Unsupported file_content message type for SHA256 computation"
        )

    @staticmethod
    def __get_file_caption(file_msg: GeneralFileMessage) -> str:
        caption = f"{file_msg.caption}\n" if file_msg.caption else ""
        if file_msg.tags and file_msg.tags.sha256:
            caption += f"#sha256IS{file_msg.tags.sha256}"
        return caption

    @staticmethod
    def __report(uploaded: int, total_size: int) -> None:
        pass

    async def __send_file(self, file_msg: GeneralFileMessage) -> SentFileMessage:
        message_id: int = EMPTY_FILE_MESSAGE

        async def on_complete():
            nonlocal message_id
            message_id = (
                await uploader.send(
                    self.__message_api.private_channel_id,
                    self.__get_file_caption(file_msg),
                )
            ).message_id

        uploader = create_uploader(self.__message_api.tdlib, file_msg, on_complete)
        size = await uploader.upload(file_msg, self.__report, file_msg.name)

        return SentFileMessage(message_id=message_id, size=size)

    async def _check_sha256(
        self, file_msg: FileMessageFromPath | FileMessageFromBuffer
    ) -> Optional[SentFileMessage]:
        sha256 = await self.__sha256(file_msg)
        file_msg.tags = FileTags(sha256=sha256)

        existing_file_msg = await self.__message_api.search_messages(
            f"#sha256IS{sha256}"
        )

        for msg in existing_file_msg:
            if not msg.document:
                continue
            logger.info(f"File with SHA256 {sha256} already exists, skipping upload")
            return SentFileMessage(
                message_id=msg.message_id,
                size=msg.document.size,
            )

        return None

    async def _save(self, file_msg: GeneralFileMessage) -> SentFileMessage:
        if isinstance(file_msg, FileMessageFromPath | FileMessageFromBuffer) and (
            msg := await self._check_sha256(file_msg)
        ):
            return msg
        return await self.__send_file(file_msg)

    @staticmethod
    def _size_for_parts(size: int) -> Generator[int]:
        part_size = 1024 * 1024 * 1024  # 1 GB

        parts = (size + part_size - 1) // part_size
        for i in range(parts - 1):
            yield part_size
        yield size - (parts - 1) * part_size

    async def save(self, file_msg: GeneralFileMessage) -> List[SentFileMessage]:
        size = file_msg.get_size()

        res: List[SentFileMessage] = []
        file_name = file_msg.name or "unnamed"

        for i, part_size in enumerate(self._size_for_parts(size)):
            file_msg.name = f"{file_name}.part{i + 1}"

            logger.info(f"Saving {file_msg.name}")
            if isinstance(file_msg, FileMessageFromBuffer | FileMessageFromPath):
                file_msg.offset += part_size
            file_msg.size = part_size
            res.append(await self._save(file_msg))

        return res

    async def update(self, message_id: int, buffer: bytes, name: str) -> int:
        file_msg: FileMessageFromBuffer = FileMessageFromBuffer.new(
            buffer=buffer,
            name=name,
        )

        async def on_complete():
            await uploader.client.edit_message_media(
                EditMessageMediaReq(
                    chat_id=self.__message_api.private_channel_id,
                    message_id=message_id,
                    file=uploader.get_uploaded_file(),
                )
            )

        uploader = create_uploader(self.__message_api.tdlib, file_msg, on_complete)
        await uploader.upload(file_msg, self.__report, file_msg.name)
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
