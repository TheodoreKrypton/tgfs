from typing import List

from asgidav.folder import Folder as _Folder
from asgidav.member import Member
from tgfs.app.fs_cache import FSCache, gfc
from tgfs.core import Client, Ops
from tgfs.utils.time import FIRST_DAY_OF_EPOCH, ts

from .resource import Resource


class ReadonlyFolder(_Folder):
    def __init__(self, path: str, sub_folders: List[str]):
        super().__init__(path)
        self._member_names = frozenset(sub_folders)

    async def display_name(self) -> str:
        return "Readonly Folder"

    async def member_names(self):
        return self._member_names

    async def member(self, path: str):
        if path == "":
            return self
        if path in self._member_names:
            return ReadonlyFolder(f"{self.path}{path}", [])
        raise NotImplementedError("ReadonlyFolder does not support nested retrieval")

    async def create_empty_resource(self, path: str) -> Member:
        raise NotImplementedError("ReadonlyFolder does not support resource creation")

    async def creation_date(self) -> int:
        return ts(FIRST_DAY_OF_EPOCH)

    async def last_modified(self) -> int:
        return ts(FIRST_DAY_OF_EPOCH)

    async def remove(self) -> None:
        raise NotImplementedError("ReadonlyFolder does not support removal")

    async def copy_to(self, destination: str) -> None:
        raise NotImplementedError("ReadonlyFolder does not support copying")

    async def move_to(self, destination: str) -> None:
        raise NotImplementedError("ReadonlyFolder does not support moving")


class Folder(_Folder):
    def __init__(self, path: str, client: Client):
        super().__init__(f"/{client.name}{path}")

        self.__relative_path = path
        self.__client = client
        self.__ops = Ops(client)
        self.__folder = client.dir_api.root if path == "/" else self.__ops.cd(path)
        self.__sub_folders = frozenset([d.name for d in self.__folder.find_dirs()])
        self.__sub_files = frozenset([f.name for f in self.__folder.find_files()])

    @property
    def fs_cache(self) -> FSCache:
        return gfc[self.__client.name]

    async def display_name(self) -> str:
        return self.__folder.name

    async def member_names(self):
        return self.__sub_folders.union(self.__sub_files)

    async def member(self, path: str):
        path_parts = path.split("/", 1)
        if path_parts[0] == "":
            return self

        if path_parts[0] in self.__sub_files:
            return Resource(self._sub_path(path_parts[0]), self.__client)

        if path_parts[0] in self.__sub_folders:
            if len(path_parts) > 1:
                return await Folder(
                    f"{self._sub_path(path_parts[0])}/", self.__client
                ).member(path_parts[1])
            return Folder(f"{self._sub_path(path_parts[0])}/", self.__client)

        return None

    def _sub_path(self, name: str):
        return f"{self.__relative_path}{name}"

    async def create_empty_resource(self, path: str):
        self.fs_cache.reset(self.__relative_path)
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
        self.fs_cache.reset(self.__relative_path)
        return await self.__ops.mkdir(self._sub_path(name), False)

    async def creation_date(self) -> int:
        return self.__folder.created_at_timestamp

    async def last_modified(self) -> int:
        return self.__folder.created_at_timestamp

    async def remove(self) -> None:
        self.fs_cache.reset_parent(self.__relative_path)
        await self.__ops.rm_dir(self.__relative_path.rstrip("/"), True)

    async def copy_to(self, destination: str) -> None:
        self.fs_cache.reset_parent(destination)
        await self.__ops.cp_dir(
            self.__relative_path.rstrip("/"), destination.rstrip("/")
        )

    async def move_to(self, destination: str) -> None:
        self.fs_cache.reset_parent(self.__relative_path)
        self.fs_cache.reset_parent(destination)
        await self.__ops.mv_dir(
            self.__relative_path.rstrip("/"), destination.rstrip("/")
        )
