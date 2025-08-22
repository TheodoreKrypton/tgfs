import asyncio
import logging
import os
from getpass import getpass
from typing import List, Optional, Sequence

from telethon import TelegramClient
from telethon import functions as tlf
from telethon import types as tlt
from telethon.errors import SessionPasswordNeededError
from telethon.helpers import TotalList
from telethon.sessions import StringSession
from telethon.tl.types import InputDocumentFileLocation, PeerChannel

from tgfs.config import Config
from tgfs.errors import TechnicalError, UnDownloadableMessage
from tgfs.reqres import (
    Document,
    DownloadFileReq,
    DownloadFileResp,
    EditMessageMediaReq,
    EditMessageTextReq,
    GetMeResp,
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
from tgfs.telegram.interface import ITDLibClient
from tgfs.utils.message_cache import channel_cache
from tgfs.utils.others import exclude_none

logger = logging.getLogger(__name__)


class TelethonAPI(ITDLibClient):
    def __init__(self, client: TelegramClient):
        super().__init__()
        self._client = client

    async def __get_messages(self, *args, **kwargs) -> Sequence[tlt.Message]:
        messages = await self._client.get_messages(*args, **kwargs)
        if not isinstance(messages, TotalList):
            raise TechnicalError("Unexpected response type from get_messages")
        return messages

    @staticmethod
    def _transform_messages(
        messages: Sequence[Optional[tlt.Message]],
    ) -> GetMessagesResp:
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

            if (
                isinstance(m.media, tlt.MessageMediaDocument)
                and (doc := m.media.document)
                and not isinstance(doc, tlt.DocumentEmpty)
            ):
                obj.document = Document(
                    size=doc.size,
                    id=doc.id,
                    access_hash=doc.access_hash,
                    file_reference=doc.file_reference,
                    mime_type=doc.mime_type,
                )

            res.append(obj)
        return res

    async def get_messages(self, req: GetMessagesReq) -> GetMessagesResp:
        cache = channel_cache(req.chat).id
        if message_id_to_fetch := cache.find_nonexistent(req.message_ids):
            fetched_messages = await self.__get_messages(
                entity=PeerChannel(channel_id=req.chat), ids=message_id_to_fetch
            )

            for message in exclude_none(self._transform_messages(fetched_messages)):
                cache[message.message_id] = message

        return GetMessagesResp(cache.gets(req.message_ids))

    async def send_text(self, req: SendTextReq) -> SendMessageResp:
        message = await self._client.send_message(
            entity=PeerChannel(channel_id=req.chat), message=req.text
        )
        return SendMessageResp(message_id=message.id)

    async def edit_message_text(self, req: EditMessageTextReq) -> SendMessageResp:
        channel_cache(req.chat).id[req.message_id] = None
        message = await self._client.edit_message(
            entity=PeerChannel(channel_id=req.chat),
            message=req.message_id,
            text=req.text,
        )
        return SendMessageResp(message_id=message.id)

    async def edit_message_media(self, req: EditMessageMediaReq) -> Message:
        channel_cache(req.chat).id[req.message_id] = None
        message = await self._client.edit_message(
            entity=PeerChannel(channel_id=req.chat),
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
        cache = channel_cache(req.chat).search
        if req.search not in cache:
            messages = await self.__get_messages(
                entity=PeerChannel(channel_id=req.chat), search=req.search
            )
            cache[req.search] = tuple(exclude_none(self._transform_messages(messages)))
        return GetMessagesRespNoNone(cache[req.search])

    async def get_pinned_messages(
        self, req: GetPinnedMessageReq
    ) -> GetMessagesRespNoNone:
        return GetMessagesRespNoNone(
            list(
                exclude_none(
                    self._transform_messages(
                        await self.__get_messages(
                            entity=PeerChannel(channel_id=req.chat),
                            filter=tlt.InputMessagesFilterPinned(),
                        )
                    )
                )
            )
        )

    async def pin_message(self, req: PinMessageReq) -> None:
        await self._client.pin_message(
            entity=PeerChannel(channel_id=req.chat),
            message=req.message_id,
            notify=False,
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
            entity=PeerChannel(channel_id=req.chat),
            file=file,
            caption=req.caption,
            force_document=True,
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
            entity=PeerChannel(channel_id=req.chat),
            file=file,
            caption=req.caption,
            force_document=True,
        )
        if not isinstance(message, tlt.Message):
            raise TechnicalError("Unexpected response type from send_file")
        return SendMessageResp(message_id=message.id)

    async def download_file(self, req: DownloadFileReq) -> DownloadFileResp:
        messages = await self.__get_messages(
            entity=PeerChannel(channel_id=req.chat), ids=[req.message_id]
        )
        message = messages[0]

        document = getattr(message, "document", None)

        if not (
            (document := getattr(message, "document", None))
            and isinstance(document, tlt.Document)
        ):
            raise UnDownloadableMessage(message.id)

        chunk_size = req.chunk_size * 1024

        bytes_to_read = req.end - req.begin + 1

        async def chunks():
            rest = bytes_to_read

            if req.end < req.begin:
                raise TechnicalError(
                    f"Invalid range: end must be greater than or equal to begin, got begin={req.begin} end={req.end}"
                )

            async for chunk in self._client.iter_download(
                file=InputDocumentFileLocation(
                    id=document.id,
                    access_hash=document.access_hash,
                    file_reference=document.file_reference,
                    thumb_size="",
                ),
                chunk_size=chunk_size,
                offset=req.begin,
            ):
                if len(chunk) > rest:
                    chunk = chunk[:rest]
                yield chunk
                rest -= len(chunk)
                if rest <= 0:
                    break

        return DownloadFileResp(chunks=chunks(), size=bytes_to_read)

    async def resolve_channel_id(self, channel_id: str) -> int:
        try:
            return int(channel_id)
        except ValueError:
            entity = await self._client.get_entity(f"@{channel_id}")
            if not isinstance(entity, tlt.Channel):
                raise TechnicalError("Expected a Telegram channel")
            return entity.id

    async def _get_me(self) -> GetMeResp:
        me = await self._client.get_me()
        if not isinstance(me, tlt.User):
            raise TechnicalError("Expected a Telegram user")
        return GetMeResp(
            name=(
                f"@{me.username}"
                if me.username
                else f"{me.first_name} {me.last_name or ''}".strip()
            ),
            is_premium=bool(me.premium),
        )


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
    if not config.telegram.account:
        raise TechnicalError("Account configuration is missing")

    api_id = config.telegram.api_id
    api_hash = config.telegram.api_hash

    session = Session(config.telegram.account.session_file)
    if sess := session.get():
        client = TelegramClient(sess, api_id, api_hash)
        await client.connect()
    else:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()

        phone_number = input("Phone number (with country code): ")
        sms_req = await client.send_code_request(phone_number, force_sms=False)
        code = input("Enter the code you received: ")

        try:
            await client.sign_in(
                phone=phone_number, code=code, phone_code_hash=sms_req.phone_code_hash
            )
        except SessionPasswordNeededError:
            password = getpass("Enter the 2FA password: ")
            await client.sign_in(password=password)
        except Exception as e:
            logger.error(f"Failed to sign in: {e}")
            raise
        session.save(client.session.save())  # type: ignore

    if (me := await client.get_me()) and isinstance(me, tlt.User) and me.username:
        logger.info(f"logged in as @{me.username}")
    else:
        logger.warning("logged in as account, but no username found")

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
            await client.connect()
        else:
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            await client.start(bot_token=token)  # type: ignore
            session.save_multibot(client.session.save())  # type: ignore

        if (me := await client.get_me()) and isinstance(me, tlt.User) and me.username:
            logger.info(f"logged in as @{me.username}")
        else:
            logger.warning("logged in as bot, but no username found")

        return client

    return await asyncio.gather(*(login(token) for token in bot_tokens))
