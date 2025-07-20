from dataclasses import dataclass
from abc import ABCMeta, abstractmethod
from typing import Optional

from tgfs.core.model import TGFSFileRef, TGFSFileDesc, TGFSMetadata
from tgfs.reqres import GeneralFileMessage, SentFileMessage, FileContent


@dataclass
class FDRepositoryResp:
    message_id: int
    fd: TGFSFileDesc


class IFileContentRepository(metaclass=ABCMeta):
    @abstractmethod
    async def save(self, file_msg: GeneralFileMessage) -> SentFileMessage:
        pass

    @abstractmethod
    async def get(
        self, name: str, message_id: int, begin: int, end: int
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
    @abstractmethod
    async def save(self, metadata: TGFSMetadata) -> None:
        pass

    @abstractmethod
    async def get(self) -> TGFSMetadata:
        pass
