from typing import AsyncIterator, Mapping, Optional, Tuple, Dict
from asgidav.folder import Folder
from asgidav.member import Member
from asgidav.resource import Resource


class MockResource(Resource):
    def __init__(self, path: str):
        super().__init__(path)

    async def content_type(self) -> str:
        return "text/plain"

    async def content_length(self) -> int:
        return 0

    async def display_name(self) -> str:
        return "test.txt"

    async def creation_date(self) -> int:
        return 1609459200000

    async def last_modified(self) -> int:
        return 1609545600000

    async def get_content(self, begin: int = 0, end: int = -1) -> AsyncIterator[bytes]:
        async def dummy_iterator():
            yield b"content"
        return dummy_iterator()

    async def overwrite(self, content: AsyncIterator[bytes], size: int) -> None:
        pass

    async def remove(self) -> None:
        pass

    async def copy_to(self, destination: str) -> None:
        pass

    async def move_to(self, destination: str) -> None:
        pass

class MockFolder(Folder):
    def __init__(self, path: str, members: Optional[Mapping[str, Member]] = None):
        super().__init__(path)
        self._members: Dict[str, Member] = {k: v for k, v in (members or {}).items()}
        self._display_name = path.split("/")[-1] or "root"
        self._creation_date = 1609459200000
        self._last_modified = 1609545600000

    async def display_name(self) -> str:
        return self._display_name

    async def creation_date(self) -> int:
        return self._creation_date

    async def last_modified(self) -> int:
        return self._last_modified

    async def member_names(self) -> Tuple[str, ...]:
        return tuple(self._members.keys())

    async def member(self, path: str) -> Member | None:
        return self._members.get(path)

    async def create_empty_resource(self, path: str) -> Member:
        resource = MockResource(path)
        self._members[path] = resource
        return resource

    async def create_folder(self, name: str) -> "Folder":
        folder = MockFolder(f"{self.path}/{name}".rstrip("/"))
        self._members[name] = folder
        return folder

    async def remove(self) -> None:
        pass

    async def copy_to(self, destination: str) -> None:
        pass

    async def move_to(self, destination: str) -> None:
        pass
