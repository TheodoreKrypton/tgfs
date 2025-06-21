from pyrate_limiter import Duration, InMemoryBucket, Limiter, Rate
from telethon.errors import MessageNotModifiedError, RPCError

from tgfs.api.client.api.message.message_broker import MessageBroker
from tgfs.api.interface import TDLibApi
from tgfs.api.types import (
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
from tgfs.errors.telegram import MessageNotFound
from tgfs.utils.others import remove_none

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
            await self.tdlib.bot.send_text(
                SendTextReq(chat_id=self.private_channel_id, text=message)
            )
        ).message_id

    async def edit_message_text(self, message_id: int, message: str) -> int:
        self.__try_acquire("MessageApi.edit_message_text")
        try:
            return (
                await self.tdlib.bot.edit_message_text(
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
        return await self.tdlib.bot.pin_message(
            PinMessageReq(chat_id=self.private_channel_id, message_id=message_id)
        )

    async def search_messages(self, search: str) -> list[MessageResp]:
        self.__try_acquire("MessageApi.search_messages")
        return list(
            remove_none(
                await self.tdlib.account.search_messages(
                    SearchMessageReq(chat_id=self.private_channel_id, search=search)
                )
            )
        )

    async def download_file(
        self, message_id: int, begin: int, end: int
    ) -> DownloadFileResp:
        return await self.tdlib.account.download_file(
            DownloadFileReq(
                chat_id=self.private_channel_id,
                message_id=message_id,
                chunk_size=get_config().tgfs.download.chunk_size_kb,
                begin=begin,
                end=end,
            )
        )
