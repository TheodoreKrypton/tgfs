import asyncio
import os.path
from typing import Optional

from asgidav.resource import Resource as _Resource
from tgfs.core import Client, Ops
from tgfs.core.model import TGFSFileDesc, TGFSFileRef
from tgfs.errors import TechnicalError
from tgfs.reqres import FileContent
from tgfs.app.global_fs_cache import gfc


class Resource(_Resource):
    def __init__(self, path: str, client: Client):
        super().__init__(f"/{client.name}{path}")

        self.__relative_path = path
        self.__client = client
        self.__fs_cache = gfc[client.name]
        self.__ops = Ops(client)

        if not (fr := self.__ops.stat_file(path)):
            raise TechnicalError(f"Resource {path} does not exist")

        self.__fr: TGFSFileRef = fr
        self.__fd_value: Optional[TGFSFileDesc] = None
        self.__lock = asyncio.Lock()

    async def __fd(self) -> TGFSFileDesc:
        async with self.__lock:
            if self.__fd_value is None:
                self.__fd_value = await self.__ops.desc(self.__relative_path)
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
            self.__relative_path,
            begin,
            end,
            os.path.basename(self.__relative_path),
        )

    async def overwrite(self, content: FileContent, size: int) -> None:
        self.__fs_cache.reset(self.__relative_path)
        await self.__ops.upload_from_stream(content, size, self.__relative_path)

    async def remove(self) -> None:
        self.__fs_cache.reset_parent(self.__relative_path)
        await self.__ops.rm_file(self.__relative_path)

    async def copy_to(self, destination: str) -> None:
        self.__fs_cache.reset_parent(destination)
        await self.__ops.cp_file(self.__relative_path, destination)

    async def move_to(self, destination: str) -> None:
        self.__fs_cache.reset_parent(self.__relative_path)
        self.__fs_cache.reset_parent(destination)
        await self.__ops.mv_file(self.__relative_path, destination)
