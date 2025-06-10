import os
from abc import ABCMeta, abstractmethod
import asyncio
from typing import Callable, Optional, Generic, TypeVar
from dataclasses import dataclass
import logging
import aiofiles
from typing import Coroutine, Any

from telethon.utils import get_appropriated_part_size
from telethon.errors import RPCError

from tgfs.api.client.api.model import (
    FileMessageFromBuffer,
    FileMessageFromPath,
    FileMessageFromStream,
    GeneralFileMessage,
)
from tgfs.api.interface import ITDLibClient, TDLibApi
from tgfs.api.types import (
    SaveBigFilePartReq,
    SaveFilePartReq,
    SendMessageResp,
    SendFileReq,
    UploadedFile,
)
from tgfs.api.utils import generate_file_id
from tgfs.errors.telegram import FileSizeTooLarge


logger = logging.getLogger(__name__)


@dataclass
class WorkersConfig:
    small: int = 3
    big: int = 5


@dataclass
class UploadingChunk:
    chunk: bytes
    file_part: int


T = TypeVar("T", FileMessageFromBuffer, FileMessageFromPath, FileMessageFromStream)
OnComplete = Callable[[], Coroutine[Any, Any, None]]


class IFileUploader(Generic[T], metaclass=ABCMeta):
    def __init__(
        self,
        client: ITDLibClient,
        file_size: int,
        on_complete: OnComplete,
        workers=WorkersConfig(),
    ):
        self._client = client
        self._file_size = file_size
        self.__on_complete = on_complete
        self.__workers = workers

        self._file_id = generate_file_id()
        self.__file_name = ""

        self.__is_big = self.__is_big_file(file_size)
        self.__part_cnt = 0
        self.__read_size = 0
        self.__uploaded_size = 0

        self.__errors: dict[int, Exception] = {}

        self.__num_workers = (
            self.__workers.big if self.__is_big else self.__workers.small
        )
        self.__uploading_chunks: list[Optional[UploadingChunk]] = [
            None
        ] * self.__num_workers
        self.__lock = asyncio.Lock()

    @staticmethod
    def __is_big_file(size: int) -> bool:
        return size >= 10 * 1024 * 1024  # 10 MB threshold

    @property
    @abstractmethod
    def _default_file_name(self) -> str:
        pass

    @abstractmethod
    async def _prepare(self, file: T) -> None:
        pass

    async def _close(self) -> None:
        pass

    @abstractmethod
    async def _read(self, length: int) -> bytes:
        pass

    @property
    def __chunk_size(self) -> int:
        return get_appropriated_part_size(self._file_size) * 1024

    @property
    def __parts(self) -> int:
        quotient, remainder = divmod(self._file_size, self.__chunk_size)
        return quotient if remainder == 0 else quotient + 1

    async def __upload_chunk(
        self, worker_id: int, chunk: bytes, file_part: int
    ) -> None:
        self.__uploading_chunks[worker_id] = UploadingChunk(
            chunk=chunk,
            file_part=file_part,
        )

        while True:
            try:
                if self.__is_big:
                    rsp = await self._client.save_big_file_part(
                        SaveBigFilePartReq(
                            file_id=self._file_id,
                            bytes=chunk,
                            file_part=file_part,
                            file_total_parts=self.__parts,
                        )
                    )
                else:
                    rsp = await self._client.save_file_part(
                        SaveFilePartReq(
                            file_id=self._file_id,
                            bytes=chunk,
                            file_part=file_part,
                        )
                    )

                if rsp.success:
                    self.__uploading_chunks[worker_id] = None
                    self.__uploaded_size += len(chunk)
                    return

            except RPCError as e:
                if e.message == "FILE_PARTS_INVALID":
                    raise FileSizeTooLarge(self._file_size) from e
            except Exception as e:
                logger.error(f"{self.__file_name} {e}")

    async def __save_uncompleted_chunks(self) -> None:
        while True:
            uncompleted_chunks = [c for c in self.__uploading_chunks if c is not None]
            if not uncompleted_chunks:
                break

            for c in uncompleted_chunks:
                if c:
                    await self.__upload_chunk(0, c.chunk, c.file_part)

    def __done_reading(self) -> bool:
        return self.__read_size >= self._file_size

    async def __upload_next_part(self, worker_id: int) -> int:
        with self.__lock:
            if self.__done_reading():
                return 0

            chunk_length = (
                self._file_size - self.__read_size
                if self.__read_size + self.__chunk_size
                else self.__chunk_size
            )

            self.__read_size += chunk_length
            self.__part_cnt += 1
            file_part = self.__part_cnt

            if chunk_length <= 0:
                return 0

            chunk = await self._read(chunk_length)

        await self.__upload_chunk(worker_id, chunk, file_part)
        return chunk_length

    async def upload(
        self,
        file: T,
        callback: Optional[Callable[[int, int], None]] = None,
        file_name: Optional[str] = None,
    ) -> int:
        loop = asyncio.get_running_loop()
        await self._prepare(file)
        self.__file_name = file_name or file.name or self._default_file_name

        async def create_worker(worker_id: int) -> bool:
            try:
                while not self.__done_reading():
                    part_size = await self.__upload_next_part(worker_id)
                    logger.info(
                        f"[Worker {worker_id}] {self.__uploaded_size * 100 / self._file_size}% uploaded {self._file_id}({self.__file_name})"
                    )

                    if part_size and callback:
                        callback(self.__read_size, self._file_size)

                return True
            except Exception as e:
                logger.error(f"Worker {worker_id} failed: {e}")
                self.__errors[worker_id] = e
                return False

        while self.__uploaded_size < self._file_size:
            futures: list[asyncio.Future[bool]] = [
                loop.create_task(create_worker(worker_id))
                for worker_id in range(self.__num_workers)
            ]
            await asyncio.gather(*futures)
            await self.__save_uncompleted_chunks()

        await asyncio.sleep(0.5)
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

    async def send(self, chat_id: int, caption: str = "") -> SendMessageResp:
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
        else:
            return await self._client.send_small_file(req)


class UploaderFromPath(IFileUploader[FileMessageFromPath]):
    async def _prepare(self, file_msg: FileMessageFromPath) -> None:
        self.__file_path = file_msg.path
        self.__file = await aiofiles.open(self.__file_path, "rb")

    async def _close(self) -> None:
        await self.__file.close()

    @property
    def _default_file_name(self) -> str:
        return os.path.basename(self.__file_path)

    async def _read(self, length: int) -> bytes:
        return await self.__file.read(length)


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
    async def _read(self, length: int) -> bytes:
        return await self.__stream.read(length)

    async def _prepare(self, file_msg: FileMessageFromStream) -> None:
        self.__stream = file_msg.stream

    async def _default_file_name(self) -> str:
        return "unnamed"


def create_uploader(
    tdlib: TDLibApi,
    file_msg: GeneralFileMessage,
    on_complete: OnComplete = lambda: None,
):
    def select_api(size: int) -> ITDLibClient:
        if size >= 50 * 1024 * 1024:
            return tdlib.account
        return tdlib.bot

    if isinstance(file_msg, FileMessageFromPath):
        file_size = os.path.getsize(file_msg.path)
        return UploaderFromPath(
            client=select_api(file_size),
            file_size=file_size,
            on_complete=on_complete,
        )

    elif isinstance(file_msg, FileMessageFromBuffer):
        file_size = len(file_msg.buffer)
        return UploaderFromBuffer(
            client=select_api(file_size),
            file_size=file_size,
            on_complete=on_complete,
        )

    elif isinstance(file_msg, FileMessageFromStream):
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
