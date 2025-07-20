import asyncio
from typing import Iterator

from pyrate_limiter import Duration, InMemoryBucket, Limiter, Rate
from telethon.errors import MessageNotModifiedError, RPCError

from tgfs.telegram.interface import TDLibApi
from tgfs.reqres import (
    DownloadFileReq,
    DownloadFileResp,
    EditMessageTextReq,
    GetPinnedMessageReq,
    MessageResp,
    PinMessageReq,
    SearchMessageReq,
    SendTextReq,
)
from tgfs.config import get_config
from tgfs.errors import MessageNotFound
from tgfs.utils.others import exclude_none, is_big_file

from .message_broker import MessageBroker
from .chained_async_iterator import ChainedAsyncIterator

rate = Rate(20, Duration.SECOND)
bucket = InMemoryBucket([rate])
limiter = Limiter(bucket, max_delay=60 * 1000)  # 60 seconds max delay


class MessageApi(MessageBroker):
    def __init__(self, tdlib: TDLibApi):
        super().__init__(tdlib)

    @staticmethod
    def __try_acquire(name: str):
        limiter.try_acquire(name)

    async def send_text(self, message: str) -> int:
        self.__try_acquire("MessageApi.send_text")
        return (
            await self.tdlib.next_bot.send_text(
                SendTextReq(chat_id=self.private_channel_id, text=message)
            )
        ).message_id

    async def edit_message_text(self, message_id: int, message: str) -> int:
        self.__try_acquire("MessageApi.edit_message_text")
        try:
            return (
                await self.tdlib.next_bot.edit_message_text(
                    EditMessageTextReq(
                        chat_id=self.private_channel_id,
                        message_id=message_id,
                        text=message,
                    )
                )
            ).message_id
        except MessageNotModifiedError:
            return message_id
        except RPCError as e:
            if e.message == "Message to edit not found":
                raise MessageNotFound(message_id=message_id)
            if e.message == "Message is not modified":
                return message_id
            raise e

    async def get_pinned_message(self) -> MessageResp:
        self.__try_acquire("MessageApi.get_pinned_message")
        messages = await self.tdlib.account.get_pinned_messages(
            GetPinnedMessageReq(chat_id=self.private_channel_id)
        )
        return messages[0]

    async def pin_message(self, message_id: int):
        self.__try_acquire("MessageApi.pin_message")
        return await self.tdlib.next_bot.pin_message(
            PinMessageReq(chat_id=self.private_channel_id, message_id=message_id)
        )

    async def search_messages(self, search: str) -> list[MessageResp]:
        self.__try_acquire("MessageApi.search_messages")
        return list(
            exclude_none(
                await self.tdlib.account.search_messages(
                    SearchMessageReq(chat_id=self.private_channel_id, search=search)
                )
            )
        )

    @classmethod
    def split_download_tasks(
        cls, begin: int, end: int, n: int
    ) -> Iterator[tuple[int, int]]:
        length = end - begin + 1
        length_per_chunk = length // n

        for i in range(n - 1):
            b = begin + i * length_per_chunk
            e = b + length_per_chunk - 1
            yield b, e

        yield begin + (n - 1) * length_per_chunk, end

    @staticmethod
    def size(begin: int, end: int) -> int:
        return begin - end + 1

    async def download_file_parallel(self, message_id: int, begin: int, end: int):
        tasks = [
            self.tdlib.next_bot.download_file(
                DownloadFileReq(
                    chat_id=self.private_channel_id,
                    message_id=message_id,
                    chunk_size=get_config().tgfs.download.chunk_size_kb,
                    begin=b,
                    end=e,
                )
            )
            for b, e in self.split_download_tasks(begin, end, len(self.tdlib.bots))
        ]

        res = [t.chunks for t in await asyncio.gather(*tasks)]
        return DownloadFileResp(
            chunks=ChainedAsyncIterator(*res), size=self.size(begin, end)
        )

    async def download_file(
        self, message_id: int, begin: int, end: int
    ) -> DownloadFileResp:
        if end > 0 and is_big_file(self.size(begin, end)):
            return await self.download_file_parallel(message_id, begin, end)

        return await self.tdlib.next_bot.download_file(
            DownloadFileReq(
                chat_id=self.private_channel_id,
                message_id=message_id,
                chunk_size=get_config().tgfs.download.chunk_size_kb,
                begin=begin,
                end=end,
            )
        )
