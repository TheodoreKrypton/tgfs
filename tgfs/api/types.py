from dataclasses import dataclass
from typing import Iterable, Optional, AsyncIterator

from telethon.tl.types import PeerChannel


@dataclass
class Message:
    message_id: int

@dataclass
class SentFileMessage(Message):
    size: int

@dataclass
class Chat:
    chat_id: PeerChannel

@dataclass
class GetMessagesReq(Chat):
    message_ids: Iterable[int]

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

GetMessagesResp = list[MessageResp]

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

@dataclass
class DownloadFileResp:
    chunks: AsyncIterator[bytes]
    size: int
