import pytest
from tgfs.utils.chained_async_iterator import ChainedAsyncIterator


class MockAsyncIterable:
    def __init__(self, items):
        self.items = items
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


class TestChainedAsyncIterator:
    @pytest.mark.asyncio
    async def test_chained_async_iterator_single(self):
        mock_iter = MockAsyncIterable([b"chunk1", b"chunk2", b"chunk3"])
        chained = ChainedAsyncIterator([mock_iter])
        
        results = []
        async for chunk in chained:
            results.append(chunk)
            
        assert results == [b"chunk1", b"chunk2", b"chunk3"]

    @pytest.mark.asyncio
    async def test_chained_async_iterator_multiple(self):
        mock_iter1 = MockAsyncIterable([b"a1", b"a2"])
        mock_iter2 = MockAsyncIterable([b"b1", b"b2", b"b3"])
        mock_iter3 = MockAsyncIterable([b"c1"])
        
        chained = ChainedAsyncIterator([mock_iter1, mock_iter2, mock_iter3])
        
        results = []
        async for chunk in chained:
            results.append(chunk)
            
        assert results == [b"a1", b"a2", b"b1", b"b2", b"b3", b"c1"]

    @pytest.mark.asyncio
    async def test_chained_async_iterator_empty(self):
        chained = ChainedAsyncIterator([])
        
        results = []
        async for chunk in chained:
            results.append(chunk)
            
        assert results == []

    @pytest.mark.asyncio
    async def test_chained_async_iterator_empty_iterables(self):
        mock_iter1 = MockAsyncIterable([])
        mock_iter2 = MockAsyncIterable([])
        
        chained = ChainedAsyncIterator([mock_iter1, mock_iter2])
        
        results = []
        async for chunk in chained:
            results.append(chunk)
            
        assert results == []

    @pytest.mark.asyncio
    async def test_chained_async_iterator_mixed_empty(self):
        mock_iter1 = MockAsyncIterable([b"data1"])
        mock_iter2 = MockAsyncIterable([])
        mock_iter3 = MockAsyncIterable([b"data2"])
        
        chained = ChainedAsyncIterator([mock_iter1, mock_iter2, mock_iter3])
        
        results = []
        async for chunk in chained:
            results.append(chunk)
            
        assert results == [b"data1", b"data2"]