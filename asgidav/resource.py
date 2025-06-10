from abc import abstractmethod

from asgidav.member import Member, Properties
from asgidav.byte_pipe import BytePipe


class ResourceProperties(Properties):
    getcontentlength: int


class Resource(Member):
    @abstractmethod
    async def content_length(self):
        pass

    @abstractmethod
    async def display_name(self):
        pass

    @abstractmethod
    async def get_content(self, begin: int = -1, end: int = -1) -> BytePipe:
        pass

    async def get_properties(self) -> ResourceProperties:
        properties = await Member.get_properties(self)
        return ResourceProperties(
            **properties,
            getcontentlength=await self.content_length(),
        )
