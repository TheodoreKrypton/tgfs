import pytest
from asgidav.async_map import async_map


class TestAsyncMap:
    @pytest.mark.asyncio
    async def test_async_map_basic(self):
        async def double(x):
            return x * 2

        result = await async_map(double, [1, 2, 3, 4])
        assert result == [2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_async_map_empty(self):
        async def identity(x):
            return x

        result = await async_map(identity, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_async_map_with_strings(self):
        async def add_suffix(s):
            return f"{s}_processed"

        result = await async_map(add_suffix, ["a", "b", "c"])
        assert result == ["a_processed", "b_processed", "c_processed"]

    @pytest.mark.asyncio
    async def test_async_map_preserves_order(self):
        async def slow_process(x):
            import asyncio
            # Simulate different processing times
            await asyncio.sleep(0.01 * (5 - x))
            return x * 10

        result = await async_map(slow_process, [1, 2, 3, 4, 5])
        assert result == [10, 20, 30, 40, 50]