import asyncio
import logging
import os
from getpass import getpass
from typing import List, Optional, Tuple  # noqa: F401

from lru import LRU
from telethon import TelegramClient
from telethon import functions as tlf
from telethon import types as tlt
from telethon.errors import SessionPasswordNeededError
from telethon.helpers import TotalList
from telethon.sessions import StringSession
from telethon.tl.types import InputDocumentFileLocation

from tgfs.api.interface import ITDLibClient
from tgfs.api.types import (
    Document,
    DownloadFileReq,
    DownloadFileResp,
    EditMessageMediaReq,
    EditMessageTextReq,
    GetMessagesReq,
    GetMessagesResp,
    GetMessagesRespNoNone,
    GetPinnedMessageReq,
    Message,
    MessageResp,
    PinMessageReq,
    SaveBigFilePartReq,
    SaveFilePartReq,
    SaveFilePartResp,
    SearchMessageReq,
    SendFileReq,
    SendMessageResp,
    SendTextReq,
)
from tgfs.config import Config
from tgfs.errors.base import TechnicalError
from tgfs.errors.tgfs import UnDownloadableMessage
from tgfs.utils.others import exclude_none

logger = logging.getLogger(__name__)


message_cache_by_id = LRU(1024)  # type: LRU[int, MessageResp]
message_cache_by_search = LRU(1024)  # type: LRU[str, Tuple[MessageResp, ...]]


def remove_message_cache_by_id(message_id: int) -> None:
    if message_id in message_cache_by_id:
        message_cache_by_id.pop(message_id)


class TelethonAPI(ITDLibClient):
    def __init__(self, client: TelegramClient):
        self._client = client

    async def __get_messages(self, *args, **kwargs) -> List[tlt.Message]:
        messages = await self._client.get_messages(*args, **kwargs)
        if not isinstance(messages, TotalList):
            raise TechnicalError("Unexpected response type from get_messages")
        return messages

    @staticmethod
    def __transform_messages(messages: List[tlt.Message]) -> GetMessagesResp:
        res = GetMessagesResp()

        for m in messages:
            if not m:
                res.append(None)
                continue

            obj = MessageResp(
                message_id=m.id,
                text="",
                document=None,
            )

            if m.message:
                obj.text = m.message

            if (doc := getattr(m, "document", None)) and isinstance(doc, tlt.Document):
                obj.document = Document(
                    size=doc.size,
                    id=doc.id,
                    access_hash=doc.access_hash,
                    file_reference=doc.file_reference,
                )

            res.append(obj)
        return res

    @classmethod
    def get_cached_messages(cls, req: GetMessagesReq) -> GetMessagesResp:
        return GetMessagesResp(
            [message_cache_by_id.get(message_id) for message_id in req.message_ids]
        )

    async def get_messages(self, req: GetMessagesReq) -> GetMessagesResp:
        message_id_to_fetch = [
            message_id
            for message_id in req.message_ids
            if message_cache_by_id.get(message_id) is None
        ]

        if message_id_to_fetch:
            fetched_messages = await self.__get_messages(
                entity=req.chat_id, ids=message_id_to_fetch
            )

            for message in exclude_none(self.__transform_messages(fetched_messages)):
                message_cache_by_id[message.message_id] = message

        return [message_cache_by_id.get(message_id) for message_id in req.message_ids]

    async def send_text(self, req: SendTextReq) -> SendMessageResp:
        message = await self._client.send_message(entity=req.chat_id, message=req.text)
        return SendMessageResp(message_id=message.id)

    async def edit_message_text(self, req: EditMessageTextReq) -> SendMessageResp:
        remove_message_cache_by_id(req.message_id)
        message = await self._client.edit_message(
            entity=req.chat_id, message=req.message_id, text=req.text
        )
        return SendMessageResp(message_id=message.id)

    async def edit_message_media(self, req: EditMessageMediaReq) -> Message:
        remove_message_cache_by_id(req.message_id)
        message = await self._client.edit_message(
            entity=req.chat_id,
            message=req.message_id,
            file=tlt.InputFile(
                id=req.file.id,
                parts=req.file.parts,
                name=req.file.name,
                md5_checksum="",
            ),
        )
        return Message(message_id=message.id)

    async def search_messages(self, req: SearchMessageReq) -> GetMessagesRespNoNone:
        if req.search not in message_cache_by_search:
            messages = await self.__get_messages(entity=req.chat_id, search=req.search)
            message_cache_by_search[req.search] = tuple(
                exclude_none(self.__transform_messages(messages))
            )
        return GetMessagesRespNoNone(message_cache_by_search[req.search])

    async def get_pinned_messages(
        self, req: GetPinnedMessageReq
    ) -> GetMessagesRespNoNone:
        return GetMessagesRespNoNone(
            list(
                exclude_none(
                    self.__transform_messages(
                        await self.__get_messages(
                            entity=req.chat_id, filter=tlt.InputMessagesFilterPinned()
                        )
                    )
                )
            )
        )

    async def pin_message(self, req: PinMessageReq) -> None:
        await self._client.pin_message(
            entity=req.chat_id, message=req.message_id, notify=False
        )

    async def save_big_file_part(self, req: SaveBigFilePartReq) -> SaveFilePartResp:
        success = await self._client(
            tlf.upload.SaveBigFilePartRequest(
                file_id=req.file_id,
                file_part=req.file_part,
                bytes=req.bytes,
                file_total_parts=req.file_total_parts,
            )
        )
        return SaveFilePartResp(success=success)

    async def save_file_part(self, req: SaveFilePartReq) -> SaveFilePartResp:
        success = await self._client(
            tlf.upload.SaveFilePartRequest(
                file_id=req.file_id,
                file_part=req.file_part,
                bytes=req.bytes,
            )
        )
        return SaveFilePartResp(success=success)

    async def send_big_file(self, req: SendFileReq) -> SendMessageResp:
        file = tlt.InputFileBig(
            id=req.file.id,
            parts=req.file.parts,
            name=req.file.name,
        )
        message = await self._client.send_file(
            entity=req.chat_id, file=file, caption=req.caption, force_document=True
        )
        if not isinstance(message, tlt.Message):
            raise TechnicalError("Unexpected response type from send_file")
        return SendMessageResp(message_id=message.id)

    async def send_small_file(self, req: SendFileReq) -> SendMessageResp:
        file = tlt.InputFile(
            id=req.file.id,
            parts=req.file.parts,
            name=req.file.name,
            md5_checksum="",
        )
        message = await self._client.send_file(
            entity=req.chat_id, file=file, caption=req.caption, force_document=True
        )
        if not isinstance(message, tlt.Message):
            raise TechnicalError("Unexpected response type from send_file")
        return SendMessageResp(message_id=message.id)

    async def download_file(self, req: DownloadFileReq) -> DownloadFileResp:
        messages = await self.__get_messages(entity=req.chat_id, ids=[req.message_id])
        message = messages[0]

        document = getattr(message, "document", None)

        if not (
            (document := getattr(message, "document", None))
            and isinstance(document, tlt.Document)
        ):
            raise UnDownloadableMessage(message.id)

        chunk_size = req.chunk_size * 1024

        async def chunks():
            bytes_to_read = (
                document.size - req.begin if req.end < 0 else req.end - req.begin + 1
            )
            async for chunk in self._client.iter_download(
                file=InputDocumentFileLocation(
                    id=document.id,
                    access_hash=document.access_hash,
                    file_reference=document.file_reference,
                    thumb_size="",
                ),
                chunk_size=chunk_size,
                offset=req.begin if req.begin >= 0 else 0,
            ):
                if len(chunk) > bytes_to_read:
                    chunk = chunk[:bytes_to_read]
                yield chunk
                if req.end >= 0:
                    bytes_to_read -= len(chunk)
                    if bytes_to_read <= 0:
                        break

        return DownloadFileResp(chunks=chunks(), size=document.size)


class Session:
    def __init__(self, session_file: str):
        self.session_file = session_file

    def get(self) -> Optional[StringSession]:
        if os.path.exists(self.session_file):
            with open(self.session_file, "r") as f:
                return StringSession(f.read().strip())
        return None

    def save_multibot(self, session_string: str):
        dir_ = os.path.dirname(self.session_file)
        if os.path.isfile(dir_):
            raise Exception(
                f"{dir_} is a session file which only supports one bot session. "
                f"Please remove the file to upgrade to multi-bot version."
            )
        os.makedirs(dir_, exist_ok=True)
        with open(self.session_file, "w") as f:
            f.write(session_string)

    def save(self, session_string: str):
        if not os.path.exists(self.session_file):
            dir_ = os.path.dirname(self.session_file)
            os.makedirs(dir_, exist_ok=True)
        with open(self.session_file, "w") as f:
            f.write(session_string)


async def login_as_account(config: Config) -> TelegramClient:
    api_id = config.telegram.api_id
    api_hash = config.telegram.api_hash

    session = Session(config.telegram.account.session_file)
    if sess := session.get():
        client = TelegramClient(sess, api_id, api_hash)
        await client.connect()

        if (me := await client.get_me()) and isinstance(me, tlt.User):
            logger.info(f"logged in as account @{me.username}")
        else:
            logger.warning("logged in as account, but no username found")

        return client

    phone_number = input("Phone Number: ")
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start()  # type: ignore
    await client.connect()

    sms_req = await client.send_code_request(phone_number, force_sms=False)
    code = input("Login code: ")

    try:
        await client.sign_in(
            phone_number, code=code, phone_code_hash=sms_req.phone_code_hash
        )
    except SessionPasswordNeededError:
        password = getpass("Enter the 2FA password: ")
        await client.sign_in(password=password)

    session.save(client.session.save())  # type: ignore

    return client


async def login_as_bots(config: Config) -> List[TelegramClient]:
    api_id = config.telegram.api_id
    api_hash = config.telegram.api_hash

    bot_tokens = config.telegram.bot.tokens or [config.telegram.bot.token]

    async def login(token: str) -> TelegramClient:
        bot_id, _ = token.split(":")

        session = Session(
            os.path.join(config.telegram.bot.session_file, f"{bot_id}.session")
        )

        if sess := session.get():
            client = TelegramClient(sess, api_id, api_hash)
        else:
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.start(bot_token=token)  # type: ignore
            session.save_multibot(client.session.save())  # type: ignore

        await client.connect()

        if (me := await client.get_me()) and isinstance(me, tlt.User):
            logger.info(f"logged in as account @{me.username}")
        else:
            logger.warning("logged in as account, but no username found")

        return client

    return await asyncio.gather(*(login(token) for token in bot_tokens))
