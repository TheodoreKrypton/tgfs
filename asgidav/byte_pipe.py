import asyncio


class BytePipe:
    def __init__(self):
        self._queue = asyncio.Queue()
        self.__current_chunk = b""
        self.__end = False

    async def write(self, data: bytes):
        await self._queue.put(data)

    async def read(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            if not self.__current_chunk:
                if self.__end and self._queue.empty():
                    break
                self.__current_chunk = await self._queue.get()
            chunk_size = min(size - len(data), len(self.__current_chunk))
            data.extend(self.__current_chunk[:chunk_size])
            self.__current_chunk = self.__current_chunk[chunk_size:]

        return bytes(data)

    def end(self):
        self.__end = True

    async def get_value(self) -> bytes:
        buffer = bytearray()
        while not self._queue.empty():
            buffer.extend(await self._queue.get())
        return bytes(buffer)

    @classmethod
    def empty(cls) -> "BytePipe":
        pipe = cls()
        pipe.end()
        return pipe
