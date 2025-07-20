from dataclasses import dataclass
from abc import ABCMeta, abstractmethod
from typing import Optional

from tgfs.core.model import TGFSFileRef, TGFSFileDesc, TGFSMetadata


@dataclass
class FDRepositoryResp:
    message_id: int
    fd: TGFSFileDesc


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
    async def save(self, metadata: TGFSMetadata) -> int:
        pass

    @abstractmethod
    async def get(self) -> TGFSMetadata:
        pass
