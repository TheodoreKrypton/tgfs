import os
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Tuple, Union

from telethon.tl.types import PeerChannel

from tgfs.tasks.integrations import TaskTracker


@dataclass
class Message:
    message_id: int


@dataclass
class SentFileMessage(Message):
    size: int


@dataclass
class Chat:
    chat: PeerChannel


@dataclass
class GetMessagesReq(Chat):
    message_ids: Tuple[int, ...]


@dataclass
class Document:
    size: int
    id: int
    access_hash: int
    file_reference: bytes


@dataclass
class MessageResp(Message):
    text: str
    document: Optional[Document]


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
    sha256: Optional[str] = None


@dataclass
class FileMessage:
    name: str
    caption: str
    tags: FileTags
    offset: int
    size: int

    task_tracker: Optional[TaskTracker]

    def _get_size(self) -> int:
        return 0

    def get_size(self) -> int:
        return self.size or self._get_size()


@dataclass
class FileMessageEmpty(FileMessage):
    @classmethod
    def new(cls, name: str = "unnamed") -> "FileMessageEmpty":
        return cls(
            name=name,
            caption="",
            tags=FileTags(),
            offset=0,
            size=0,
            task_tracker=None,
        )


@dataclass
class FileMessageFromPath(FileMessage):
    path: str

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
        )


@dataclass
class FileMessageFromBuffer(FileMessage):
    buffer: bytes

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
        )


@dataclass
class FileMessageFromStream(FileMessage):
    stream: FileContent

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
        )


GeneralFileMessage = Union[
    FileMessageEmpty, FileMessageFromPath, FileMessageFromBuffer, FileMessageFromStream
]
