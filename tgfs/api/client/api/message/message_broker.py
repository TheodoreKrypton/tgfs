import asyncio
from dataclasses import dataclass
from functools import reduce
from typing import List, Optional, Set

from tgfs.api.interface import TDLibApi
from tgfs.api.types import GetMessagesReq, GetMessagesResp, MessageResp
from tgfs.config import get_config

DELAY = 0.1


@dataclass
class Request:
    ids: list[int]
    future: asyncio.Future[GetMessagesResp]


class MessageBroker:
    @property
    def private_channel_id(self):
        return get_config().telegram.private_file_channel

    def __init__(self, tdlib: TDLibApi):
        self.tdlib = tdlib
        self.__requests: List[Request] = []
        self.__lock = asyncio.Lock()
        self.__task: Optional[asyncio.Task] = None

    async def get_messages(self, ids: list[int]) -> list[Optional[MessageResp]]:
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        async with self.__lock:
            self.__requests.append(Request(ids, future))
            if self.__task and not self.__task.done():
                self.__task.cancel()
            self.__task = loop.create_task(self.process_requests())
        return await future

    async def process_requests(self):
        try:
            await asyncio.sleep(DELAY)

            async with self.__lock:
                requests, self.__requests = self.__requests, []

            if not requests:
                return

            ids: Set[int] = reduce(
                lambda full, req: full.union(req.ids), requests, set()
            )
            messages = await self.tdlib.account.get_messages(
                GetMessagesReq(chat_id=self.private_channel_id, message_ids=tuple(ids))
            )

            messages_map = {msg.message_id: msg for msg in messages if msg is not None}

            for r in requests:
                if not r.future.done():
                    r.future.set_result([messages_map.get(msg_id) for msg_id in r.ids])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            for request in requests:
                if not request.future.done():
                    request.future.set_exception(e)
