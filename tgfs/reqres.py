import os
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Tuple

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

    task_tracker: Optional[TaskTracker]

    def _get_size(self) -> int:
        return 0

    def get_size(self) -> int:
        return self.size or self._get_size()


@dataclass
class FileMessageEmpty(FileMessage):
    @classmethod
    def new(cls, name: str = "unnamed") -> "FileMessageEmpty":
        return cls(name=name, size=0)


@dataclass
class FileMessageFromPath(UploadableFileMessage):
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
class FileMessageFromBuffer(UploadableFileMessage):
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
class FileMessageFromStream(UploadableFileMessage):
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


@dataclass
class FileMessageImported(FileMessage):
    message_id: int

    @classmethod
    def new(
        cls, message_id: int, size: int, name: str = "unnamed"
    ) -> "FileMessageImported":
        return cls(name=name, size=size, message_id=message_id)
