from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from itertools import cycle
from typing import List

from tgfs.reqres import (
    DownloadFileReq,
    DownloadFileResp,
    EditMessageMediaReq,
    EditMessageTextReq,
    GetMessagesReq,
    GetMessagesResp,
    GetMessagesRespNoNone,
    GetPinnedMessageReq,
    Message,
    PinMessageReq,
    SaveBigFilePartReq,
    SaveFilePartReq,
    SaveFilePartResp,
    SearchMessageReq,
    SendFileReq,
    SendMessageResp,
    SendTextReq,
)


class ITDLibClient(metaclass=ABCMeta):
    @abstractmethod
    def get_cached_messages(self, req: GetMessagesReq) -> GetMessagesResp:
        pass

    @abstractmethod
    async def get_messages(self, req: GetMessagesReq) -> GetMessagesResp:
        pass

    @abstractmethod
    async def send_text(self, req: SendTextReq) -> SendMessageResp:
        pass

    @abstractmethod
    async def edit_message_text(self, req: EditMessageTextReq) -> SendMessageResp:
        pass

    @abstractmethod
    async def search_messages(self, req: SearchMessageReq) -> GetMessagesRespNoNone:
        pass

    @abstractmethod
    async def get_pinned_messages(
        self, req: GetPinnedMessageReq
    ) -> GetMessagesRespNoNone:
        pass

    @abstractmethod
    async def pin_message(self, req: PinMessageReq) -> None:
        pass

    @abstractmethod
    async def save_big_file_part(self, req: SaveBigFilePartReq) -> SaveFilePartResp:
        pass

    @abstractmethod
    async def save_file_part(self, req: SaveFilePartReq) -> SaveFilePartResp:
        pass

    @abstractmethod
    async def send_big_file(self, req: SendFileReq) -> SendMessageResp:
        pass

    @abstractmethod
    async def send_small_file(self, req: SendFileReq) -> SendMessageResp:
        pass

    @abstractmethod
    async def edit_message_media(self, req: EditMessageMediaReq) -> Message:
        pass

    @abstractmethod
    async def download_file(self, req: DownloadFileReq) -> DownloadFileResp:
        pass


@dataclass
class TDLibApi:
    account: ITDLibClient
    bots: List[ITDLibClient]

    def __post_init__(self):
        self.__bots_cycle = cycle(self.bots)

    @property
    def bot(self) -> ITDLibClient:
        return self.bots[0]

    @property
    def next_bot(self) -> ITDLibClient:
        return next(self.__bots_cycle)
