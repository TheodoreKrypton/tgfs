import datetime
import email.utils
import pytest
from asgidav.member import Member, Properties, ResourceType


class MockMember(Member):
    def __init__(self, path: str):
        super().__init__(path)
        self._content_type = "text/plain"
        self._content_length = 100
        self._display_name = "test.txt"
        self._creation_date = 1609459200000  # 2021-01-01 00:00:00 UTC
        self._last_modified = 1609545600000  # 2021-01-02 00:00:00 UTC

    async def content_type(self) -> str:
        return self._content_type

    async def content_length(self) -> int:
        return self._content_length

    async def display_name(self) -> str:
        return self._display_name

    async def creation_date(self) -> int:
        return self._creation_date

    async def last_modified(self) -> int:
        return self._last_modified

    async def remove(self) -> None:
        pass

    async def copy_to(self, destination: str) -> None:
        pass

    async def move_to(self, destination: str) -> None:
        pass


class TestMember:
    def test_member_init(self):
        member = MockMember("/test/path")
        assert member.path == "/test/path"
        assert member.is_hidden is False
        assert member.is_readonly is False
        assert member.is_root is False
        assert member.resource_type == ResourceType.DEFAULT

    def test_member_properties(self):
        member = MockMember("/test")
        member.is_hidden = True
        member.is_readonly = True
        member.is_root = True
        
        assert member.is_hidden is True
        assert member.is_readonly is True
        assert member.is_root is True

    @pytest.mark.asyncio
    async def test_get_properties(self):
        member = MockMember("/test.txt")
        properties = await member.get_properties()
        
        assert properties["displayname"] == "test.txt"
        assert properties["getcontenttype"] == "text/plain"
        assert properties["resourcetype"] == ""
        assert "getlastmodified" in properties
        assert "creationdate" in properties

    def test_unixdate2iso8601(self):
        timestamp = 1609459200000  # 2021-01-01 00:00:00 UTC
        result = Member.unixdate2iso8601(timestamp)
        expected = datetime.datetime.fromtimestamp(
            timestamp / 1000, tz=datetime.timezone.utc
        ).isoformat()
        assert result == expected

    def test_unixdate2rfc1123(self):
        timestamp = 1609459200000  # 2021-01-01 00:00:00 UTC
        result = Member.unixdate2rfc1123(timestamp)
        expected = email.utils.formatdate(timestamp / 1000, usegmt=True)
        assert result == expected

    def test_resource_type_enum(self):
        assert ResourceType.DEFAULT.value == ""
        assert ResourceType.COLLECTION.value == "collection"

    @pytest.mark.asyncio
    async def test_abstract_methods_implemented(self):
        member = MockMember("/test")
        
        assert await member.content_type() == "text/plain"
        assert await member.content_length() == 100
        assert await member.display_name() == "test.txt"
        assert await member.creation_date() == 1609459200000
        assert await member.last_modified() == 1609545600000
        
        # These should not raise NotImplementedError
        await member.remove()
        await member.copy_to("/destination")
        await member.move_to("/destination")