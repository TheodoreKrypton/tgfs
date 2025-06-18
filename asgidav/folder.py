from abc import abstractmethod
from typing import Tuple

from asgidav.member import Member, Properties, ResourceType


class FolderProperties(Properties):
    childcount: int


class Folder(Member):
    resource_type: ResourceType = ResourceType.COLLECTION

    async def content_type(self) -> str:
        return "httpd/unix-directory"

    @abstractmethod
    async def display_name(self) -> str:
        raise NotImplemented

    @abstractmethod
    async def member_names(self) -> Tuple[str, ...]:
        raise NotImplemented

    @abstractmethod
    async def member(self, name) -> Member | None:
        raise NotImplemented

    async def create_empty_resource(self, name: str) -> Member:
        raise NotImplemented

    async def create_folder(self, name: str) -> "Folder":
        raise NotImplemented

    async def get_properties(self) -> FolderProperties:
        properties = await Member.get_properties(self)
        return FolderProperties(
            **properties,
            childcount=len(await self.member_names()),
        )
