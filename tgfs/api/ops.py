import os.path
from typing import AsyncIterator

from asgidav.byte_pipe import BytePipe

from tgfs.errors.path import InvalidPath, FileOrDirectoryDoesNotExist
from tgfs.model.directory import TGFSDirectory, TGFSFileRef
from tgfs.model.file import TGFSFile
from .client.api.client import Client
from .client.api.model import (
    FileMessageEmpty,
    FileTags,
    FileMessageFromPath,
    FileMessageFromBuffer,
    FileMessageFromStream,
)


class Ops:
    def __init__(self, client: Client):
        self.__client = client

    @staticmethod
    def __validate_path(path: str) -> None:
        if path[-1] == "/" or path[0] != "/":
            raise InvalidPath(path)

    def cd(self, path: str) -> TGFSDirectory:
        path_parts = filter(lambda x: x, path.split("/"))

        current_dir = self.__client.dir_api.root

        for part in path_parts:
            if part == "..":
                current_dir = current_dir.parent
            elif part == ".":
                continue
            else:
                current_dir = current_dir.find_dir(part)
        return current_dir

    def ls(self, path: str) -> TGFSFileRef | list[TGFSDirectory | TGFSFileRef]:
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)
        next_dir = d

        if basename:
            try:
                next_dir = d.find_dir(basename)
            except FileOrDirectoryDoesNotExist:
                next_dir = None

        if next_dir:
            return self.__client.dir_api.ls(next_dir)
        else:
            # cannot find a subdirectory with the given name, so assume it's a file
            return self.__client.dir_api.ls(d, basename)

    async def desc(self, path: str) -> TGFSFile:
        file_ref = self.ls(path)
        if not isinstance(file_ref, TGFSFileRef):
            raise FileOrDirectoryDoesNotExist(path)
        return await self.__client.file_api.desc(file_ref)

    async def cp_dir(
        self, path_from: str, path_to: str
    ) -> tuple[TGFSDirectory, TGFSDirectory]:
        self.__validate_path(path_from)

        dirname_from, basename_from = os.path.dirname(path_from), os.path.basename(
            path_from
        )

        d = self.cd(dirname_from)
        dir_to_copy = d.find_dir(basename_from)

        dirname_to, basename_to = os.path.dirname(path_to), os.path.basename(path_to)
        d2 = self.cd(dirname_to)

        res = await self.__client.dir_api.create(
            basename_to or basename_to, d2, dir_to_copy
        )

        return dir_to_copy, res

    async def cp_file(
        self, path_from: str, path_to: str
    ) -> tuple[TGFSFileRef, TGFSFileRef]:
        self.__validate_path(path_from)

        dirname_from, basename_from = os.path.dirname(path_from), os.path.basename(
            path_from
        )

        d = self.cd(dirname_from)
        file_to_copy = d.find_file(basename_from)

        dirname_to, basename_to = os.path.dirname(path_to), os.path.basename(path_to)
        d2 = self.cd(dirname_to)

        res = await self.__client.file_api.copy(
            d2, file_to_copy, basename_to or basename_from
        )

        return file_to_copy, res

    async def mkdir(self, path: str, parents: bool) -> TGFSDirectory:
        self.__validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)

        if parents:
            # Create all parent directories if they do not exist
            for part in filter(lambda x: x, dirname.split("/")):
                try:
                    d = d.find_dir(part)
                except FileOrDirectoryDoesNotExist:
                    # If the directory does not exist, create it
                    d = await self.__client.dir_api.create(part, d)
        res = await self.__client.dir_api.create(basename, d)
        return res

    async def touch(self, path: str) -> None:
        self.__validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)

        try:
            d.find_file(basename)
        except FileOrDirectoryDoesNotExist:
            await self.__client.file_api.upload(
                d, FileMessageEmpty(name=basename, caption="", tags=FileTags())
            )

    async def mv_dir(self, path_from: str, path_to: str) -> TGFSDirectory:
        dir_from, dir_to = await self.cp_dir(path_from, path_to)
        await self.__client.dir_api.rm_dangerously(dir_from)
        return dir_to

    async def mv_file(self, path_from: str, path_to: str) -> TGFSFileRef:
        file_from, file_to = await self.cp_file(path_from, path_to)
        await self.__client.file_api.rm(file_from)
        return file_to

    async def rm_dir(self, path: str, recursive: bool) -> TGFSDirectory:
        self.__validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)
        dir_to_remove = d.find_dir(basename)

        if recursive:
            await self.__client.dir_api.rm_dangerously(dir_to_remove)
        else:
            await self.__client.dir_api.rm_empty(dir_to_remove)

        return dir_to_remove

    async def rm_file(self, path: str) -> TGFSFileRef:
        self.__validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)
        file_to_remove = d.find_file(basename)

        await self.__client.file_api.rm(file_to_remove)

        return file_to_remove

    async def upload_from_local(self, local: str, remote: str) -> TGFSFile:
        if not os.path.exists(local) or not os.path.isfile(local):
            raise FileOrDirectoryDoesNotExist(local)

        self.__validate_path(remote)
        dirname, basename = os.path.dirname(remote), os.path.basename(remote)

        d = self.cd(dirname)

        return await self.__client.file_api.upload(
            d,
            FileMessageFromPath(name=basename, caption="", tags=FileTags(), path=local),
        )

    async def upload_from_bytes(self, data: bytes, remote: str) -> TGFSFile:
        self.__validate_path(remote)
        dirname, basename = os.path.dirname(remote), os.path.basename(remote)

        d = self.cd(dirname)

        return await self.__client.file_api.upload(
            d,
            FileMessageFromBuffer(
                name=basename,
                caption="",
                tags=FileTags(),
                buffer=data,
            ),
        )

    async def upload_from_stream(
        self, stream: BytePipe, size: int, remote: str
    ) -> TGFSFile:
        self.__validate_path(remote)
        dirname, basename = os.path.dirname(remote), os.path.basename(remote)

        d = self.cd(dirname)

        return await self.__client.file_api.upload(
            d,
            FileMessageFromStream(
                name=basename, caption="", tags=FileTags(), stream=stream, size=size
            ),
        )

    async def download(self, path: str, as_name: str) -> AsyncIterator[bytes]:
        self.__validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)
        file_ref = d.find_file(basename)

        if not file_ref:
            raise FileOrDirectoryDoesNotExist(path)

        return await self.__client.file_api.retrieve(file_ref, as_name)
