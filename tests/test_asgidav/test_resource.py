import pytest
from typing import AsyncIterator
from .common import MockResource as _MockResource


class MockResource(_MockResource):
    def __init__(self, path: str, content_length: int = 100):
        super().__init__(path)
        self._content_length = content_length
        self._display_name = "test.txt"
        self._creation_date = 1609459200000
        self._last_modified = 1609545600000

    async def content_length(self) -> int:
        return self._content_length

    async def display_name(self) -> str:
        return self._display_name

    async def creation_date(self) -> int:
        return self._creation_date

    async def last_modified(self) -> int:
        return self._last_modified

    async def get_content(self, begin: int = 0, end: int = -1) -> AsyncIterator[bytes]:
        async def chunks(b, e):
            content = b"test content" * 10
            if e == -1:
                e = len(content)
            for i in range(b, min(e + 1, len(content)), 8):
                yield content[i : i + 8]

        return chunks(begin, end)


class TestResource:
    @pytest.mark.asyncio
    async def test_get_properties(self):
        resource = MockResource("/test.txt", content_length=150)
        properties = await resource.get_properties()

        assert properties["getcontentlength"] == "150"
        assert properties["displayname"] == "test.txt"
        assert properties["getcontenttype"] == "text/plain"

    @pytest.mark.asyncio
    async def test_get_properties_zero_length(self):
        resource = MockResource("/empty.txt", content_length=0)
        properties = await resource.get_properties()

        assert properties["getcontentlength"] == "0"

    @pytest.mark.asyncio
    async def test_get_properties_negative_length(self):
        resource = MockResource("/test.txt")
        resource._content_length = -5
        properties = await resource.get_properties()

        # Should be max(0, -5) = 0
        assert properties["getcontentlength"] == "0"

    @pytest.mark.asyncio
    async def test_get_content(self):
        resource = MockResource("/test.txt")
        content_chunks = []
        async for chunk in await resource.get_content():
            content_chunks.append(chunk)

        assert len(content_chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in content_chunks)

    @pytest.mark.asyncio
    async def test_get_content_with_range(self):
        resource = MockResource("/test.txt")
        content_chunks = []
        async for chunk in await resource.get_content(begin=5, end=15):
            content_chunks.append(chunk)

        assert len(content_chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in content_chunks)

    @pytest.mark.asyncio
    async def test_abstract_methods(self):
        resource = MockResource("/test.txt")

        assert await resource.content_length() == 100
        assert await resource.display_name() == "test.txt"
        assert await resource.content_type() == "text/plain"

        # These should not raise NotImplementedError

        async def dummy_content():
            yield b"dummy content"

        await resource.overwrite(dummy_content(), 11)
        await resource.remove()
        await resource.copy_to("/destination")
        await resource.move_to("/destination")
