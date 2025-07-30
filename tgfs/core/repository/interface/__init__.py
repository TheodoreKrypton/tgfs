from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

from tgfs.core.model import (
    TGFSDirectory,
    TGFSFileDesc,
    TGFSFileRef,
    TGFSFileVersion,
    TGFSMetadata,
)
from tgfs.errors import MetadataNotInitialized
from tgfs.reqres import FileContent, GeneralFileMessage, SentFileMessage


@dataclass
class FDRepositoryResp:
    message_id: int
    fd: TGFSFileDesc


class IFileContentRepository(metaclass=ABCMeta):
    @abstractmethod
    async def save(self, file_msg: GeneralFileMessage) -> List[SentFileMessage]:
        pass

    @abstractmethod
    async def get(
        self,
        fv: TGFSFileVersion,
        begin: int,
        end: int,
        name: str,
    ) -> FileContent:
        pass

    @abstractmethod
    async def update(self, message_id: int, buffer: bytes, name: str) -> int:
        pass


class IFDRepository(metaclass=ABCMeta):
    @abstractmethod
    async def save(
        self, fd: TGFSFileDesc, fr: Optional[TGFSFileRef] = None
    ) -> FDRepositoryResp:
        pass

    @abstractmethod
    async def get(self, fr: TGFSFileRef) -> TGFSFileDesc:
        pass


class IMetaDataRepository(metaclass=ABCMeta):
    def __init__(self):
        self.metadata: Optional[TGFSMetadata] = None

    async def init(self):
        self.metadata = await self.get()

    @abstractmethod
    async def push(self) -> None:
        pass

    @abstractmethod
    async def get(self) -> TGFSMetadata:
        pass

    def root(self) -> TGFSDirectory:
        if not self.metadata:
            raise MetadataNotInitialized
        return self.metadata.dir
