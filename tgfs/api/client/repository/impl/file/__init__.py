import json
import aiofiles
import hashlib
import logging
from dataclasses import asdict

from tgfs.api.client.api.message import MessageApi
from tgfs.api.client.api.model import (
    FileMessageFromPath,
    FileMessageFromBuffer,
    FileMessageEmpty,
    GeneralFileMessage,
    FileMessageFromStream,
    FileTags,
)
from tgfs.api.client.repository.impl.file.file_uploader import create_uploader
from tgfs.api.types import SentFileMessage, EditMessageMediaReq
from asgidav.byte_pipe import BytePipe
from tgfs.errors.base import TechnicalError
from tgfs.model.file import EMPTY_FILE

logger = logging.getLogger(__name__)


class FileRepository:
    def __init__(self, message_api: MessageApi):
        self.__message_api = message_api

    @staticmethod
    async def __sha256(
        file_msg: FileMessageFromPath | FileMessageFromBuffer | FileMessageEmpty,
    ) -> str:
        if isinstance(file_msg, FileMessageEmpty):
            raise TechnicalError("Cannot compute SHA256 for an empty file")

        if isinstance(file_msg, FileMessageFromPath):
            sha256 = hashlib.sha256()
            async with aiofiles.open(file_msg.path, "rb") as f:
                while True:
                    chunk = await f.read(8192)
                    if not chunk:
                        break
                    sha256.update(chunk)
            return sha256.hexdigest()

        if isinstance(file_msg, FileMessageFromBuffer):
            sha256 = hashlib.sha256(file_msg.buffer)
            return sha256.hexdigest()

        raise TechnicalError("Unsupported file message type for SHA256 computation")

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
        message_id: int = EMPTY_FILE

        async def on_complete():
            nonlocal message_id
            message_id = await uploader.send(
                self.__message_api.private_channel_id, self.__get_file_caption(file_msg)
            )

        uploader = create_uploader(self.__message_api.tdlib, file_msg, on_complete)
        size = await uploader.upload(file_msg, self.__report, file_msg.name)
        logger.debug(f"File sent {json.dumps(asdict(file_msg))}")

        return SentFileMessage(message_id=message_id, size=size)

    async def save(self, file_msg: GeneralFileMessage) -> SentFileMessage:
        if isinstance(file_msg, FileMessageFromStream):
            # cannot compute sha256 for stream
            logger.debug(
                f"Sending file {json.dumps({**asdict(file_msg), 'stream': 'hidden'})}"
            )
            return await self.__send_file(file_msg)

        logger.debug(f"Sending file {json.dumps(asdict(file_msg))}")

        sha256 = await self.__sha256(file_msg)
        file_msg.tags = FileTags(sha256=sha256)

        existing_file_msg = await self.__message_api.search_messages(
            f"#sha256IS{sha256}"
        )

        if existing_file_msg:
            msg = existing_file_msg[0]
            logger.debug(f"File with SHA256 {sha256} already exists, skipping upload")
            return SentFileMessage(
                message_id=msg.message_id,
                size=msg.document.size,
            )

        return await self.__send_file(file_msg)

    async def update(self, message_id: int, buffer: bytes, name: str) -> int:
        file_msg: FileMessageFromBuffer = FileMessageFromBuffer(
            buffer=buffer, name=name, caption="", tags=FileTags()
        )

        async def on_complete():
            await self.__message_api.tdlib.bot.edit_message_media(
                EditMessageMediaReq(
                    chat_id=self.__message_api.private_channel_id,
                    message_id=message_id,
                    file=uploader.get_uploaded_file(),
                )
            )

        uploader = await create_uploader(
            self.__message_api.tdlib, file_msg, on_complete
        )
        await uploader.upload(file_msg, self.__report, file_msg.name)
        return message_id

    async def download_file(self, name: str, message_id: int) -> BytePipe:
        logger.info(f"Downloading file {name} with message ID {message_id}")
        resp = await self.__message_api.download_file(message_id)
        return resp.chunks
