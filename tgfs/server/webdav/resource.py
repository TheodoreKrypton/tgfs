import asyncio
import io
from typing import Optional

from asgidav.resource import Resource as _Resource

from tgfs.api.client.api.client import Client
from tgfs.api.ops import Ops
from tgfs.model.file import TGFSFile


class Resource(_Resource):
    def __init__(self, path: str, client: Client):
        super().__init__(path)
        self.__client = client
        self.__ops = Ops(client)
        self.__fr = self.__ops.ls(path)
        self.__fd_value: Optional[TGFSFile] = None
        self.__lock = asyncio.Lock()

    async def __fd(self) -> TGFSFile:
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

    async def get_content(self, begin: int = -1, end: int = -1) -> io.BytesIO:
        res = io.BytesIO()

        async def pipe_content():
            pipe = await self.__ops.download(self.path, "unnamed")
            while True:
                chunk = await pipe.read(8192)
                if not chunk:
                    break
                res.write(chunk)

        pipe_content()
        return res
