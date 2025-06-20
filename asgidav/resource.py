from abc import abstractmethod
from typing import AsyncIterator

from asgidav.member import Member, Properties


class ResourceProperties(Properties):
    getcontentlength: str


class Resource(Member):
    @abstractmethod
    async def content_length(self):
        pass

    @abstractmethod
    async def display_name(self):
        pass

    @abstractmethod
    async def get_content(self, begin: int = 0, end: int = -1) -> AsyncIterator[bytes]:
        pass

    async def get_properties(self) -> ResourceProperties:
        properties = await Member.get_properties(self)
        return ResourceProperties(
            **properties, getcontentlength=str(max(0, await self.content_length()))
        )

    @abstractmethod
    async def write(self, content: AsyncIterator[bytes], size: int) -> None:
        raise NotImplementedError
