from asgidav.cache import fs_cache
from asgidav.folder import Folder as _Folder
from tgfs.core import Client, Ops

from .resource import Resource


class Folder(_Folder):
    def __init__(self, path: str, client: Client):
        super().__init__(path)
        self.__client = client
        self.__ops = Ops(client)
        self.__folder = client.dir_api.root if path == "/" else self.__ops.cd(path)
        self.__sub_folders = frozenset([d.name for d in self.__folder.find_dirs()])
        self.__sub_files = frozenset([f.name for f in self.__folder.find_files()])

        self.__is_root = path == "/"

    async def display_name(self) -> str:
        return self.__folder.name

    async def member_names(self):
        return self.__sub_folders.union(self.__sub_files)

    async def member(self, path: str):
        names = path.split("/", 1)

        if names[0] == "":
            return self

        if names[0] in self.__sub_files:
            return Resource(self._sub_path(names[0]), self.__client)

        if names[0] in self.__sub_folders:
            if len(names) > 1:
                return await Folder(
                    f"{self._sub_path(names[0])}/", self.__client
                ).member(names[1])
            return Folder(f"{self._sub_path(names[0])}/", self.__client)

        return None

    def _sub_path(self, name: str):
        return f"{self.path}{name}"

    async def create_empty_resource(self, path: str):
        fs_cache.reset(self.path)
        names = path.split("/", 1)

        if len(names) > 1:
            sub_folder = await self.member(names[0])
            if not isinstance(sub_folder, Folder):
                raise ValueError(f"{self._sub_path(names[0])} is not a folder")
            return await sub_folder.create_empty_resource(names[1])

        if names[0] == "":
            raise ValueError("the requested path is a folder")

        if names[0] not in self.__sub_files:
            await self.__ops.touch(self._sub_path(names[0]))

        return Resource(self._sub_path(names[0]), self.__client)

    async def create_folder(self, name: str):
        fs_cache.reset(self.path)
        return await self.__ops.mkdir(self._sub_path(name), False)

    async def creation_date(self) -> int:
        return self.__folder.created_at_timestamp

    async def last_modified(self) -> int:
        return self.__folder.created_at_timestamp

    async def remove(self) -> None:
        fs_cache.reset_parent(self.path)
        await self.__ops.rm_dir(self.path.rstrip("/"), True)

    async def copy_to(self, destination: str) -> None:
        fs_cache.reset_parent(destination)
        await self.__ops.cp_dir(self.path.rstrip("/"), destination.rstrip("/"))

    async def move_to(self, destination: str) -> None:
        fs_cache.reset_parent(self.path)
        fs_cache.reset_parent(destination)
        await self.__ops.mv_dir(self.path.rstrip("/"), destination.rstrip("/"))
