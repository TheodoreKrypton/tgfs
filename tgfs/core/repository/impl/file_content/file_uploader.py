import asyncio
import logging
import os
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Generic, Optional, TypeVar

from telethon.errors import RPCError
from telethon.helpers import generate_random_long
from telethon.tl.types import PeerChannel
from telethon.utils import get_appropriated_part_size

from tgfs.errors import FileSizeTooLarge, TechnicalError
from tgfs.reqres import (
    FileMessageFromBuffer,
    FileMessageFromPath,
    FileMessageFromStream,
    GeneralFileMessage,
    SaveBigFilePartReq,
    SaveFilePartReq,
    SendFileReq,
    SendMessageResp,
    UploadedFile,
)
from tgfs.telegram.interface import ITDLibClient, TDLibApi
from tgfs.utils.others import is_big_file

logger = logging.getLogger(__name__)


@dataclass
class WorkersConfig:
    small: int = 3
    big: int = 5


@dataclass
class FileChunk:
    content: bytes
    file_part: int


T = TypeVar("T", FileMessageFromBuffer, FileMessageFromPath, FileMessageFromStream)
OnComplete = Callable[[], Coroutine[Any, Any, None]]


class IFileUploader(Generic[T], metaclass=ABCMeta):
    def __init__(
        self,
        client: ITDLibClient,
        file_size: int,
        on_complete: Optional[OnComplete],
        workers=WorkersConfig(),
    ):
        self._client = client
        self._file_size = file_size
        self.__chunk_size = get_appropriated_part_size(self._file_size) * 1024

        self.__on_complete = on_complete
        self.__workers = workers

        self._file_id = generate_random_long()
        self.__file_name = ""

        self.__is_big = is_big_file(file_size)
        self.__part_cnt = -1
        self.__read_size = 0
        self.__uploaded_size = 0

        self.__errors: dict[int, Exception] = {}

        self.__num_workers = (
            self.__workers.big if self.__is_big else self.__workers.small
        )
        self.__uncompleted_chunks: asyncio.Queue[FileChunk] = asyncio.Queue()
        self.__lock = asyncio.Lock()

    @property
    @abstractmethod
    def _default_file_name(self) -> str:
        pass

    @abstractmethod
    async def _prepare(self, file_msg: T) -> None:
        pass

    async def _close(self) -> None:
        pass

    @abstractmethod
    async def _read(self, length: int) -> bytes:
        pass

    @property
    def __parts(self) -> int:
        return (self._file_size + self.__chunk_size - 1) // self.__chunk_size

    async def __upload_chunk(self, chunk: FileChunk) -> None:
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if self.__is_big:
                    rsp = await self._client.save_big_file_part(
                        SaveBigFilePartReq(
                            file_id=self._file_id,
                            bytes=chunk.content,
                            file_part=chunk.file_part,
                            file_total_parts=self.__parts,
                        )
                    )
                else:
                    rsp = await self._client.save_file_part(
                        SaveFilePartReq(
                            file_id=self._file_id,
                            bytes=chunk.content,
                            file_part=chunk.file_part,
                        )
                    )

                if not rsp.success:
                    raise TechnicalError(f"Unexpected response: {rsp}")

                self.__uploaded_size += len(chunk.content)
                return

            except RPCError as e:
                if e.message == "FILE_PARTS_INVALID":
                    raise FileSizeTooLarge(self._file_size) from e
                logger.warning(
                    f"RPC error uploading part {chunk.file_part} for {self.__file_name}: {e}, attempt={attempt + 1}"
                )
            except Exception as e:
                logger.warning(
                    f"Error uploading part {chunk.file_part} for {self.__file_name}: {e}, attempt={attempt + 1}"
                )

        await self.__uncompleted_chunks.put(chunk)

    async def __save_uncompleted_chunks(self) -> None:
        while self.__uncompleted_chunks.qsize():
            await self.__upload_chunk(await self.__uncompleted_chunks.get())

    def __done_reading(self) -> bool:
        return self.__read_size >= self._file_size

    async def __upload_next_part(self) -> int:
        async with self.__lock:
            if self.__done_reading():
                return 0

            chunk_length = (
                self._file_size - self.__read_size
                if self.__read_size + self.__chunk_size > self._file_size
                else self.__chunk_size
            )

            self.__read_size += chunk_length
            self.__part_cnt += 1
            file_part = self.__part_cnt

            if chunk_length <= 0:
                return 0

            content = await self._read(chunk_length)

        await self.__upload_chunk(FileChunk(content=content, file_part=file_part))
        return chunk_length

    async def upload(
        self,
        file: T,
        callback: Optional[Callable[[int, int], None]] = None,
        file_name: Optional[str] = None,
    ) -> int:
        await self._prepare(file)
        self.__file_name = file_name or file.name or self._default_file_name

        async def create_worker(worker_id: int) -> bool:
            try:
                while not self.__done_reading():
                    part_size = await self.__upload_next_part()
                    logger.info(
                        f"[Worker {worker_id}] {self.__uploaded_size * 100 / self._file_size}% uploaded. file_id={self._file_id} file_name={self.__file_name}"
                    )

                    if part_size and callback:
                        callback(self.__read_size, self._file_size)

                return True
            except Exception as e:
                logger.error(f"Worker {worker_id} failed: {e}")
                self.__errors[worker_id] = e
                return False

        while self.__uploaded_size < self._file_size:
            await asyncio.gather(
                *(create_worker(worker_id) for worker_id in range(self.__num_workers))
            )
            await self.__save_uncompleted_chunks()

        await asyncio.sleep(0.5)

        if self.__on_complete:
            await self.__on_complete()

        await self._close()
        return self._file_size

    @property
    def errors(self) -> list[Exception]:
        return list(self.__errors.values())

    def get_uploaded_file(self) -> UploadedFile:
        return UploadedFile(
            id=self._file_id,
            parts=self.__parts,
            name=self.__file_name,
        )

    async def send(self, chat_id: PeerChannel, caption: str = "") -> SendMessageResp:
        logger.info(
            f"Sending file {self.__file_name} ({self._file_id}) to chat {chat_id}"
        )

        req = SendFileReq(
            chat_id=chat_id,
            file=self.get_uploaded_file(),
            name=self.__file_name,
            caption=caption,
        )

        if self.__is_big:
            return await self._client.send_big_file(req)
        return await self._client.send_small_file(req)


class UploaderFromPath(IFileUploader[FileMessageFromPath]):
    async def _prepare(self, file_msg: FileMessageFromPath) -> None:
        self.__file_path = file_msg.path
        self.__file = open(self.__file_path, "rb")

    async def _close(self) -> None:
        self.__file.close()

    @property
    def _default_file_name(self) -> str:
        return os.path.basename(self.__file_path)

    async def _read(self, length: int) -> bytes:
        return self.__file.read(length)


class UploaderFromBuffer(IFileUploader[FileMessageFromBuffer]):
    async def _prepare(self, file_msg: FileMessageFromBuffer) -> None:
        self.__buffer = file_msg.buffer

    @property
    def _default_file_name(self) -> str:
        return "unnamed"

    async def _read(self, length: int) -> bytes:
        chunk = self.__buffer[:length]
        self.__buffer = self.__buffer[length:]
        return chunk


class UploaderFromStream(IFileUploader[FileMessageFromStream]):
    async def _prepare(self, file_msg: FileMessageFromStream) -> None:
        self.__stream = file_msg.stream
        self.__current: bytes = b""
        self.__begin = 0

    def __rest_len(self) -> int:
        return len(self.__current) - self.__begin

    async def _read(self, length: int) -> bytes:
        res = bytearray()

        while len(res) < length:
            res.extend(self.__read_from_current(length - len(res)))
            if self.__rest_len() == 0:
                self.__current = await anext(self.__stream)
                self.__begin = 0
        return bytes(res)

    def __read_from_current(self, length: int):
        end = self.__begin + min(length, self.__rest_len())
        res = self.__current[self.__begin : end]
        self.__begin = end
        return res

    @property
    def _default_file_name(self) -> str:
        return "unnamed"


def create_uploader(
    tdlib: TDLibApi,
    file_msg: GeneralFileMessage,
    on_complete: Optional[OnComplete] = None,
):
    def select_api(size: int) -> ITDLibClient:
        return tdlib.account if is_big_file(size) else tdlib.bot

    if isinstance(file_msg, FileMessageFromPath):
        file_size = os.path.getsize(file_msg.path)
        return UploaderFromPath(
            client=select_api(file_size),
            file_size=file_size,
            on_complete=on_complete,
        )

    if isinstance(file_msg, FileMessageFromBuffer):
        file_size = len(file_msg.buffer)
        return UploaderFromBuffer(
            client=select_api(file_size),
            file_size=file_size,
            on_complete=on_complete,
        )

    if isinstance(file_msg, FileMessageFromStream):
        file_size = file_msg.size
        return UploaderFromStream(
            client=select_api(file_size),
            file_size=file_size,
            on_complete=on_complete,
        )

    raise ValueError(
        f"Unsupported file message type: {type(file_msg)}. "
        "Expected FileMessageFromPath, FileMessageFromBuffer, or FileMessageFromStream."
    )
