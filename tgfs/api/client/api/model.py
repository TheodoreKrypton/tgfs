from dataclasses import dataclass
from typing import Union, Optional

from tgfs.model.file import TGFSFile
from tgfs.api.utils.byte_pipe import BytePipe


@dataclass
class FileDescAPIResponse:
    message_id: int
    fd: TGFSFile


@dataclass
class FileTags:
    sha256: Optional[str] = None


@dataclass
class FileMessage:
    name: str
    caption: str
    tags: FileTags


@dataclass
class FileMessageEmpty(FileMessage):
    pass


@dataclass
class FileMessageFromPath(FileMessage):
    path: str


@dataclass
class FileMessageFromBuffer(FileMessage):
    buffer: bytes


@dataclass
class FileMessageFromStream(FileMessage):
    stream: BytePipe
    size: int


GeneralFileMessage = Union[
    FileMessageEmpty, FileMessageFromPath, FileMessageFromBuffer, FileMessageFromStream
]
