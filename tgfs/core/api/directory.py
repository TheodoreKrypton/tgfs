from typing import List, Optional

from tgfs.core.model import TGFSDirectory, TGFSFileRef
from tgfs.errors import DirectoryIsNotEmpty, FileOrDirectoryDoesNotExist

from .metadata import MetaDataApi


class DirectoryApi:
    def __init__(self, metadata_api: MetaDataApi):
        self.__metadata_api = metadata_api

    @property
    def root(self):
        return self.__metadata_api.get_root_directory()

    async def create(
        self,
        name: str,
        under: TGFSDirectory,
        dir_to_copy: Optional[TGFSDirectory] = None,
    ) -> TGFSDirectory:
        new_dir = under.create_dir(name, dir_to_copy)
        await self.__metadata_api.push()
        return new_dir

    @staticmethod
    def ls(directory: TGFSDirectory) -> List[TGFSDirectory | TGFSFileRef]:
        return directory.find_dirs() + directory.find_files()

    @staticmethod
    def get_fr(directory: TGFSDirectory, file_name: str) -> TGFSFileRef:
        if f := directory.find_file(file_name):
            return f
        raise FileOrDirectoryDoesNotExist(file_name)

    async def rm_empty(self, directory: TGFSDirectory) -> None:
        if directory.find_dirs() or directory.find_files():
            raise DirectoryIsNotEmpty(directory.absolute_path)
        await self.rm_dangerously(directory)

    async def rm_dangerously(self, directory: TGFSDirectory) -> None:
        directory.delete()
        await self.__metadata_api.push()
