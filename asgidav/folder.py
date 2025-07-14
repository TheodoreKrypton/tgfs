from abc import abstractmethod
from typing import Tuple

from asgidav.member import Member, Properties, ResourceType


class FolderProperties(Properties):
    childcount: int


class Folder(Member):
    resource_type: ResourceType = ResourceType.COLLECTION

    async def content_type(self) -> str:
        return "httpd/unix-directory"

    async def content_length(self) -> int:
        return 0

    @abstractmethod
    async def member_names(self) -> Tuple[str, ...]:
        raise NotImplementedError

    @abstractmethod
    async def member(self, path: str) -> Member | None:
        raise NotImplementedError

    @abstractmethod
    async def create_empty_resource(self, path: str) -> Member:
        raise NotImplementedError

    async def create_folder(self, name: str) -> "Folder":
        raise NotImplementedError

    async def get_properties(self) -> FolderProperties:
        properties = await Member.get_properties(self)
        return FolderProperties(
            **properties,
            childcount=len(await self.member_names()),
        )
