from typing import Optional

from tgfs.api.client.api.metadata import MetaDataApi
from tgfs.errors.path import FileOrDirectoryDoesNotExist, DirectoryIsNotEmpty
from tgfs.model.directory import TGFSDirectory, TGFSFileRef
from tgfs.utils.validate_name import validate_name


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
        validate_name(name)
        new_dir = under.create_dir(name, dir_to_copy)
        await self.__metadata_api.update()
        return new_dir

    @staticmethod
    def ls(
        directory: TGFSDirectory, file_name: Optional[str] = None
    ) -> TGFSFileRef | list[TGFSDirectory | TGFSFileRef]:
        if file_name:
            if f := directory.find_file(file_name):
                return f
            raise FileOrDirectoryDoesNotExist(file_name)
        return directory.find_dirs() + directory.find_files()

    async def rm_empty(self, directory: TGFSDirectory) -> None:
        if directory.find_dirs() or directory.find_files():
            raise DirectoryIsNotEmpty(directory.absolute_path)
        await self.rm_dangerously(directory)

    async def rm_dangerously(self, directory: TGFSDirectory) -> None:
        directory.delete()
        await self.__metadata_api.update()
