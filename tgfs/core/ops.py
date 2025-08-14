import os.path
from typing import AsyncIterator

from tgfs.errors import FileOrDirectoryDoesNotExist, InvalidPath
from tgfs.reqres import (
    FileMessageEmpty,
    FileMessageFromBuffer,
    FileMessageFromPath,
    FileMessageFromStream,
    FileMessageImported,
    MessageRespWithDocument,
)

from .client import Client
from .model import TGFSDirectory, TGFSFileDesc, TGFSFileRef


class Ops:
    def __init__(self, client: Client):
        self._client = client

    @staticmethod
    def _validate_path(path: str) -> None:
        if path[-1] == "/" or path[0] != "/":
            raise InvalidPath(path)

    def cd(self, path: str) -> TGFSDirectory:
        current_dir = self._client.dir_api.root

        for part in path.split("/"):
            if part == "..":
                current_dir = current_dir.parent
            elif part == "." or not part:
                continue
            else:
                current_dir = current_dir.find_dir(part)

        return current_dir

    def stat_file(self, path: str) -> TGFSFileRef:
        self._validate_path(path)

        dirname, basename = os.path.dirname(path), os.path.basename(path)
        d = self.cd(dirname)

        # cannot find a subdirectory with the given name, so assume it's a file_content
        res = self._client.dir_api.get_fr(d, basename)

        return res

    async def desc(self, path: str) -> TGFSFileDesc:
        file_ref = self.stat_file(path)
        res = await self._client.file_api.desc(file_ref)
        return res

    async def cp_dir(
        self, path_from: str, path_to: str
    ) -> tuple[TGFSDirectory, TGFSDirectory]:
        self._validate_path(path_from)

        dirname_from, basename_from = os.path.dirname(path_from), os.path.basename(
            path_from
        )

        d = self.cd(dirname_from)
        dir_to_copy = d.find_dir(basename_from)

        dirname_to, basename_to = os.path.dirname(path_to), os.path.basename(path_to)
        d2 = self.cd(dirname_to)

        res = await self._client.dir_api.create(
            basename_to or basename_from, d2, dir_to_copy
        )

        return dir_to_copy, res

    async def cp_file(
        self, path_from: str, path_to: str
    ) -> tuple[TGFSFileRef, TGFSFileRef]:
        self._validate_path(path_from)

        dirname_from, basename_from = os.path.dirname(path_from), os.path.basename(
            path_from
        )

        d = self.cd(dirname_from)
        file_to_copy = d.find_file(basename_from)

        dirname_to, basename_to = os.path.dirname(path_to), os.path.basename(path_to)
        d2 = self.cd(dirname_to)

        res = await self._client.file_api.copy(
            d2, file_to_copy, basename_to or basename_from
        )

        return file_to_copy, res

    async def mkdir(self, path: str, parents: bool) -> TGFSDirectory:
        self._validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)

        if parents:
            # Create all parent directories if they do not exist
            for part in filter(lambda x: x, dirname.split("/")):
                try:
                    d = d.find_dir(part)
                except FileOrDirectoryDoesNotExist:
                    # If the directory does not exist, create it
                    d = await self._client.dir_api.create(part, d)
        return await self._client.dir_api.create(basename, d)

    async def touch(self, path: str) -> None:
        self._validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)

        try:
            d.find_file(basename)
        except FileOrDirectoryDoesNotExist:
            await self._client.file_api.upload(d, FileMessageEmpty.new(name=basename))

    async def mv_dir(self, path_from: str, path_to: str) -> TGFSDirectory:
        dir_from, dir_to = await self.cp_dir(path_from, path_to)
        await self._client.dir_api.rm_dangerously(dir_from)
        return dir_to

    async def mv_file(self, path_from: str, path_to: str) -> TGFSFileRef:
        file_from, file_to = await self.cp_file(path_from, path_to)
        await self._client.file_api.rm(file_from)
        return file_to

    async def rm_dir(self, path: str, recursive: bool) -> TGFSDirectory:
        self._validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)
        dir_to_remove = d.find_dir(basename)

        if recursive:
            await self._client.dir_api.rm_dangerously(dir_to_remove)
        else:
            await self._client.dir_api.rm_empty(dir_to_remove)

        return dir_to_remove

    async def rm_file(self, path: str) -> TGFSFileRef:
        self._validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)
        file_to_remove = d.find_file(basename)

        await self._client.file_api.rm(file_to_remove)

        return file_to_remove

    async def upload_from_local(self, local: str, remote: str) -> TGFSFileDesc:
        if not os.path.exists(local) or not os.path.isfile(local):
            raise FileOrDirectoryDoesNotExist(local)

        self._validate_path(remote)
        dirname, basename = os.path.dirname(remote), os.path.basename(remote)

        d = self.cd(dirname)

        return await self._client.file_api.upload(
            d,
            FileMessageFromPath.new(
                path=local,
                name=basename,
            ),
        )

    async def upload_from_bytes(self, data: bytes, remote: str) -> TGFSFileDesc:
        self._validate_path(remote)
        dirname, basename = os.path.dirname(remote), os.path.basename(remote)

        d = self.cd(dirname)

        return await self._client.file_api.upload(
            d,
            FileMessageFromBuffer.new(
                buffer=data,
                name=basename,
            ),
        )

    async def upload_from_stream(
        self, stream: AsyncIterator[bytes], size: int, remote: str
    ) -> TGFSFileDesc:
        self._validate_path(remote)
        dirname, basename = os.path.dirname(remote), os.path.basename(remote)

        d = self.cd(dirname)

        return await self._client.file_api.upload(
            d,
            FileMessageFromStream.new(
                name=basename,
                stream=stream,
                size=size,
            ),
        )

    async def import_from_existing_file_message(
        self, message: MessageRespWithDocument, remote: str
    ) -> TGFSFileDesc:
        self._validate_path(remote)
        dirname, basename = os.path.dirname(remote), os.path.basename(remote)
        d = self.cd(dirname)

        return await self._client.file_api.upload(
            d,
            FileMessageImported.new(
                name=basename,
                size=message.document.size,
                message_id=message.message_id,
            ),
        )

    async def download(
        self,
        path: str,
        begin: int,
        end: int,
        as_name: str,
    ) -> AsyncIterator[bytes]:
        self._validate_path(path)
        dirname, basename = os.path.dirname(path), os.path.basename(path)

        d = self.cd(dirname)
        file_ref = d.find_file(basename)

        if not file_ref:
            raise FileOrDirectoryDoesNotExist(path)

        return await self._client.file_api.retrieve(
            file_ref,
            begin,
            end,
            as_name,
        )
