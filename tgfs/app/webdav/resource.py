import asyncio
import os.path
from typing import Optional

from asgidav.resource import Resource as _Resource
from tgfs.core import Client, Ops
from tgfs.core.model import TGFSFileDesc, TGFSFileRef
from tgfs.errors import TechnicalError
from tgfs.reqres import FileContent
from tgfs.app.cache import fs_cache


class Resource(_Resource):
    def __init__(self, path: str, client: Client):
        super().__init__(path)
        self.__client = client
        self.__ops = Ops(client)

        if not (fr := self.__ops.ls(path)):
            raise TechnicalError(f"Resource {path} does not exist")

        if not isinstance(fr, TGFSFileRef):
            raise TechnicalError(
                "Resource must be a file_content, not a directory or other type"
            )

        self.__fr: TGFSFileRef = fr
        self.__fd_value: Optional[TGFSFileDesc] = None
        self.__lock = asyncio.Lock()

    async def __fd(self) -> TGFSFileDesc:
        async with self.__lock:
            if self.__fd_value is None:
                self.__fd_value = await self.__ops.desc(self.path)
        return self.__fd_value

    async def creation_date(self) -> int:
        return int((await self.__fd()).created_at.timestamp())

    async def last_modified(self) -> int:
        return int((await self.__fd()).get_latest_version().updated_at_timestamp)

    async def content_length(self):
        return (await self.__fd()).get_latest_version().size

    async def content_type(self):
        return "application/octet-stream"

    async def display_name(self) -> str:
        return self.__fr.name

    async def get_content(self, begin: int = 0, end: int = -1) -> FileContent:
        return await self.__ops.download(
            self.path,
            begin,
            end,
            os.path.basename(self.path),
        )

    async def overwrite(self, content: FileContent, size: int) -> None:
        fs_cache.reset(self.path)
        await self.__ops.upload_from_stream(content, size, self.path)

    async def remove(self) -> None:
        fs_cache.reset_parent(self.path)
        await self.__ops.rm_file(self.path)

    async def copy_to(self, destination: str) -> None:
        fs_cache.reset_parent(destination)
        await self.__ops.cp_file(self.path, destination)

    async def move_to(self, destination: str) -> None:
        fs_cache.reset_parent(self.path)
        fs_cache.reset_parent(destination)
        await self.__ops.mv_file(self.path, destination)
