from dataclasses import dataclass
import asyncio
from functools import reduce
from typing import Optional

from telethon.tl import types as tlt

from tgfs.api.interface import TDLibApi
from tgfs.api.types import GetMessagesReq, GetMessagesResp
from tgfs.config import get_config


DELAY = 0.1


@dataclass
class Request:
    ids: list[int]
    future: asyncio.Future[GetMessagesResp]


class MessageBatcher:
    @property
    def private_channel_id(self):
        return get_config().telegram.private_file_channel

    def __init__(self, tdlib: TDLibApi):
        self.tdlib = tdlib
        self.__requests: list[Request] = []
        self.__lock = asyncio.Lock()
        self.__task: asyncio.Task | None = None

    async def get_messages(self, ids: list[int]) -> list[Optional[tlt.Message]]:
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        async with self.__lock:
            self.__requests.append(Request(ids, future))
            if self.__task and not self.__task.done():
                self.__task.cancel()
            self.__task = asyncio.create_task(self._call())
        return await future

    async def _call(self):
        try:
            await asyncio.sleep(DELAY)
            async with self.__lock:
                requests, self.__requests = self.__requests, []

            if not requests:
                return

            ids = reduce(lambda full, req: full.union(req.ids), requests, set())
            messages = await self.tdlib.account.get_messages(
                GetMessagesReq(chat_id=self.private_channel_id, message_ids=ids)
            )
            messages_map = {msg.message_id: msg for msg in messages}

            for r in requests:
                if r.future.done():
                    continue
                r.future.set_result([messages_map.get(msg_id) for msg_id in r.ids])

        except asyncio.CancelledError:
            return
