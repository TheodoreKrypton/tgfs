from abc import ABCMeta, abstractmethod
from typing import Optional

from tgfs.api.client.api.model import FileDescAPIResponse
from tgfs.model.file import TGFSFile
from tgfs.model.directory import TGFSFileRef
from tgfs.model.metadata import TGFSMetadata


class IFDRepository(metaclass=ABCMeta):
    @abstractmethod
    async def save(
        self, fd: TGFSFile, message_id: Optional[int] = None
    ) -> FileDescAPIResponse:
        pass

    @abstractmethod
    async def get(self, fr: TGFSFileRef) -> TGFSFile:
        pass


class IMetaDataRepository(metaclass=ABCMeta):
    @abstractmethod
    async def save(self, metadata: TGFSMetadata) -> int:
        pass

    @abstractmethod
    async def get(self) -> TGFSMetadata:
        pass
