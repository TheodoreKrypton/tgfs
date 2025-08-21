import os
from dataclasses import dataclass, field
from io import IOBase
from typing import AsyncIterator, Optional, Tuple, List

from tgfs.tasks.integrations import TaskTracker


@dataclass
class Message:
    message_id: int


@dataclass
class SentFileMessage(Message):
    size: int


@dataclass
class Chat:
    chat: int


@dataclass
class GetMessagesReq(Chat):
    message_ids: Tuple[int, ...]


@dataclass
class Document:
    size: int
    id: int
    access_hash: int
    file_reference: bytes
    mime_type: Optional[str]


@dataclass
class MessageResp(Message):
    text: str
    document: Optional[Document]


@dataclass
class MessageRespWithDocument(MessageResp):
    document: Document


GetMessagesResp = list[Optional[MessageResp]]
GetMessagesRespNoNone = list[MessageResp]


@dataclass
class SearchMessageReq(Chat):
    search: str


GetPinnedMessageReq = Chat
SendMessageResp = Message


@dataclass
class SendTextReq(Chat):
    text: str


@dataclass
class EditMessageTextReq(SendTextReq, Message):
    pass


@dataclass
class PinMessageReq(Chat, Message):
    pass


@dataclass
class SaveFilePartReq:
    file_id: int
    bytes: bytes
    file_part: int


@dataclass
class SaveBigFilePartReq(SaveFilePartReq):
    file_total_parts: int


@dataclass
class SaveFilePartResp:
    success: bool


@dataclass
class UploadedFile:
    id: int
    parts: int
    name: str


@dataclass
class FileAttr:
    name: str
    caption: str


@dataclass
class SendFileReq(Chat, FileAttr):
    file: UploadedFile


@dataclass
class EditMessageMediaReq(Chat, Message):
    file: UploadedFile


@dataclass
class DownloadFileReq(Chat, Message):
    chunk_size: int
    begin: int
    end: int


FileContent = AsyncIterator[bytes]


@dataclass
class DownloadFileResp:
    chunks: FileContent
    size: int


@dataclass
class FileTags:
    pass


@dataclass
class FileMessage:
    name: str
    size: int


@dataclass
class UploadableFileMessage(FileMessage):
    caption: str
    tags: FileTags
    offset: int
    read_size: int

    task_tracker: Optional[TaskTracker]

    def _get_size(self) -> int:
        return 0

    def get_size(self) -> int:
        return self.size or self._get_size()

    async def open(self) -> None:
        pass

    async def read(self, length: int) -> bytes:
        raise NotImplementedError("Subclasses must implement the read method")

    async def close(self) -> None:
        pass

    def file_name(self) -> str:
        return self.name or "unnamed"


@dataclass
class FileMessageEmpty(FileMessage):
    @classmethod
    def new(cls, name: str = "unnamed") -> "FileMessageEmpty":
        return cls(name=name, size=0)


@dataclass
class FileMessageFromPath(UploadableFileMessage):
    path: str
    _fd: IOBase

    def _get_size(self) -> int:
        return os.path.getsize(self.path)

    @classmethod
    def new(cls, path: str, name: str = "unnamed") -> "FileMessageFromPath":
        return cls(
            name=name,
            caption="",
            tags=FileTags(),
            path=path,
            offset=0,
            size=os.path.getsize(path),
            task_tracker=None,
            read_size=0,
            _fd=open(path, "rb"),
        )

    async def open(self) -> None:
        self._fd = open(self.path, "rb")

    async def read(self, length: int) -> bytes:
        return self._fd.read(length)

    async def close(self) -> None:
        if self._fd:
            self._fd.close()

    def file_name(self) -> str:
        return self.name or os.path.basename(self.path)


@dataclass
class FileMessageFromBuffer(UploadableFileMessage):
    buffer: bytes
    __buffer: bytes = b""

    def _get_size(self) -> int:
        return len(self.buffer)

    @classmethod
    def new(cls, buffer: bytes, name: str = "unnamed") -> "FileMessageFromBuffer":
        return cls(
            name=name,
            caption="",
            tags=FileTags(),
            buffer=buffer,
            offset=0,
            size=len(buffer),
            task_tracker=None,
            read_size=0,
        )

    async def open(self) -> None:
        self.__buffer = self.buffer[self.offset :]

    async def read(self, length: int) -> bytes:
        chunk = self.__buffer[:length]
        self.__buffer = self.__buffer[length:]
        return chunk


@dataclass
class FileMessageFromStream(UploadableFileMessage):
    stream: FileContent
    cached_chunks: List[bytes] = field(default_factory=list)
    cached_size = 0

    @classmethod
    def new(
        cls,
        stream: FileContent,
        size: int,
        name: str = "unnamed",
    ) -> "FileMessageFromStream":
        return cls(
            name=name,
            caption="",
            tags=FileTags(),
            stream=stream,
            offset=0,
            size=size,
            task_tracker=None,
            read_size=0,
        )

    async def read(self, length: int) -> bytes:
        size_to_return = min(length, self.get_size() - self.read_size)
        while self.cached_size < size_to_return:
            chunk = await anext(self.stream)
            self.cached_chunks.append(chunk)
            self.cached_size += len(chunk)

        joined = b"".join(self.cached_chunks)
        res = joined[:size_to_return]
        self.cached_chunks = [joined[size_to_return:]]
        self.cached_size -= size_to_return
        self.read_size += size_to_return
        return res


@dataclass
class FileMessageImported(FileMessage):
    message_id: int

    @classmethod
    def new(
        cls, message_id: int, size: int, name: str = "unnamed"
    ) -> "FileMessageImported":
        return cls(name=name, size=size, message_id=message_id)
