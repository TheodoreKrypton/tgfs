from typing import Optional

from tgfs.api.client.repository.interface import IMetaDataRepository
from tgfs.model.directory import TGFSDirectory
from tgfs.model.metadata import TGFSMetadata


class MetaDataApi:
    def __init__(self, metadata_repo: IMetaDataRepository):
        self.__metadata_repo = metadata_repo
        self.__metadata: Optional[TGFSMetadata] = None

    async def init(self) -> None:
        self.__metadata = await self.__metadata_repo.get()

        if not self.__metadata:
            self.reset()
            await self.update()

    def reset(self) -> None:
        self.__metadata = TGFSMetadata(dir=TGFSDirectory.root_dir(), message_id=-1)

    async def update(self) -> None:
        self.__metadata.message_id = await self.__metadata_repo.save(self.__metadata)

    def get_root_directory(self) -> TGFSDirectory:
        return self.__metadata.dir
