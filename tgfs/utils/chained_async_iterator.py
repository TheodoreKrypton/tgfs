from typing import AsyncIterable, AsyncIterator, Iterable


class ChainedAsyncIterator(AsyncIterator[bytes]):
    def __init__(self, iterators: Iterable[AsyncIterable[bytes]]):
        self.iterators: Iterable[AsyncIterable[bytes]] = iterators
        self.gen = self.generator()

    async def generator(self) -> AsyncIterator[bytes]:
        for iterator in self.iterators:
            async for chunk in iterator:
                yield chunk

    async def __anext__(self) -> bytes:
        return await anext(self.gen)
