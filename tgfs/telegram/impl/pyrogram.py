import asyncio
import logging
import os
from typing import List, Optional, Sequence, TypeVar

from pyrogram import Client, file_id
from pyrogram import enums as e
from pyrogram import types as t
from pyrogram.raw import functions as rf
from pyrogram.raw import types as rt

from tgfs.config import Config
from tgfs.errors import TechnicalError, UnDownloadableMessage
from tgfs.reqres import (
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
    GetMeResp,
)
from tgfs.telegram.interface import ITDLibClient
from tgfs.utils.message_cache import channel_cache
from tgfs.utils.others import exclude_none

logger = logging.getLogger(__name__)


T = TypeVar("T")


def assert_update[T](updates: rt.Updates, type_: type[T]) -> T:
    if len(updates.updates) > 0 and isinstance(updates.updates[0], type_):
        return updates.updates[0]
    raise TechnicalError(
        f"Expected update of type {type_.__name__}, got {type(updates.updates[0]).__name__ if updates.updates else 'None'}"
    )


class PyrogramAPI(ITDLibClient):
    def __init__(self, client: Client):
        super().__init__()
        self._client = client

    @staticmethod
    def _transform_messages(
        messages: Sequence[Optional[t.Message]],
    ) -> GetMessagesResp:
        res = GetMessagesResp()

        for m in messages:
            if not m:
                res.append(None)
                continue

            message_resp = MessageResp(
                message_id=m.id,
                text="",
                document=None,
            )

            if m.text:
                message_resp.text = m.text

            if doc := m.document:
                file_id_obj = file_id.FileId.decode(m.document.file_id)
                message_resp.document = Document(
                    size=doc.file_size,
                    id=file_id_obj.media_id,
                    access_hash=file_id_obj.access_hash,
                    file_reference=file_id_obj.file_reference,
                    mime_type=doc.mime_type,
                )
            res.append(message_resp)
        return res

    async def get_messages(self, req: GetMessagesReq) -> GetMessagesResp:
        cache = channel_cache(req.chat).id
        if message_id_to_fetch := cache.find_nonexistent(req.message_ids):
            if not (
                fetched_messages := await self._client.get_messages(
                    chat_id=req.chat, message_ids=message_id_to_fetch
                )
            ):
                raise TechnicalError(
                    f"Failed to fetch messages with ids {message_id_to_fetch} from chat {req.chat}"
                )

            if isinstance(fetched_messages, t.Message):
                fetched_messages = [fetched_messages]

            for message in exclude_none(self._transform_messages(fetched_messages)):
                cache[message.message_id] = message

        return GetMessagesResp(cache.gets(req.message_ids))

    async def send_text(self, req: SendTextReq) -> SendMessageResp:
        message = await self._client.send_message(chat_id=req.chat, text=req.text)
        return SendMessageResp(message_id=message.id)

    async def edit_message_text(self, req: EditMessageTextReq) -> SendMessageResp:
        channel_cache(req.chat).id[req.message_id] = None
        message = await self._client.edit_message_text(
            chat_id=req.chat,
            message_id=req.message_id,
            text=req.text,
        )
        return SendMessageResp(message_id=message.id)

    async def edit_message_media(self, req: EditMessageMediaReq) -> Message:
        channel_cache(req.chat).id[req.message_id] = None

        updates: rt.Updates = await self._client.invoke(
            rf.messages.EditMessage(
                peer=await self._client.resolve_peer(req.chat),  # type: ignore
                id=req.message_id,
                media=rt.InputMediaUploadedDocument(  # type: ignore
                    file=rt.InputFile(  # type: ignore
                        id=req.file.id,
                        parts=req.file.parts,
                        name=req.file.name,
                        md5_checksum="",
                    ),
                    mime_type="application/octet-stream",
                    attributes=[],
                ),
            )
        )

        update = assert_update(updates, rt.UpdateEditChannelMessage)
        message: t.Message = update.message  # type: ignore
        return Message(message_id=message.id)

    async def search_messages(self, req: SearchMessageReq) -> GetMessagesRespNoNone:
        cache = channel_cache(req.chat).search
        if req.search not in cache:
            if messages := self._client.search_messages(
                chat_id=req.chat, query=req.search
            ):
                res: List[t.Message] = []
                async for message in messages:
                    if not message:
                        continue
                    res.append(message)
                cache[req.search] = tuple(exclude_none(self._transform_messages(res)))
        return GetMessagesRespNoNone(cache[req.search])

    async def get_pinned_messages(
        self, req: GetPinnedMessageReq
    ) -> GetMessagesRespNoNone:
        if pinned_messages := self._client.search_messages(
            chat_id=req.chat, filter=e.MessagesFilter.PINNED
        ):
            async for message in pinned_messages:
                return GetMessagesRespNoNone(
                    list(exclude_none(self._transform_messages([message])))
                )
        return []

    async def pin_message(self, req: PinMessageReq) -> None:
        await self._client.pin_chat_message(
            chat_id=req.chat,
            message_id=req.message_id,
            disable_notification=True,
        )

    async def save_big_file_part(self, req: SaveBigFilePartReq) -> SaveFilePartResp:
        success = await self._client.invoke(
            rf.upload.SaveBigFilePart(
                file_id=req.file_id,
                file_part=req.file_part,
                bytes=req.bytes,
                file_total_parts=req.file_total_parts,
            )
        )
        return SaveFilePartResp(success=success)

    async def save_file_part(self, req: SaveFilePartReq) -> SaveFilePartResp:
        success = await self._client.invoke(
            rf.upload.SaveFilePart(
                file_id=req.file_id,
                file_part=req.file_part,
                bytes=req.bytes,
            )
        )
        return SaveFilePartResp(success=success)

    async def send_big_file(self, req: SendFileReq) -> SendMessageResp:
        updates: rt.Updates = await self._client.invoke(
            rf.messages.SendMedia(
                peer=await self._client.resolve_peer(req.chat),  # type: ignore
                media=rt.InputMediaUploadedDocument(  # type: ignore
                    file=rt.InputFileBig(  # type: ignore
                        id=req.file.id,
                        parts=req.file.parts,
                        name=req.file.name,
                    ),
                    mime_type="application/octet-stream",
                    attributes=[rt.DocumentAttributeFilename(file_name=req.file.name)],  # type: ignore
                ),
                message=req.caption,
                random_id=req.file.id,
            )
        )
        update = assert_update(updates, rt.UpdateMessageID)
        return SendMessageResp(message_id=update.id)

    async def send_small_file(self, req: SendFileReq) -> SendMessageResp:
        updates: rt.Updates = await self._client.invoke(
            rf.messages.SendMedia(
                peer=await self._client.resolve_peer(req.chat),  # type: ignore
                media=rt.InputMediaUploadedDocument(  # type: ignore
                    file=rt.InputFile(  # type: ignore
                        id=req.file.id,
                        parts=req.file.parts,
                        name=req.file.name,
                        md5_checksum="",
                    ),
                    mime_type="application/octet-stream",
                    attributes=[rt.DocumentAttributeFilename(file_name=req.file.name)],  # type: ignore
                ),
                message=req.caption,
                random_id=req.file.id,
            )
        )
        update = assert_update(updates, rt.UpdateMessageID)
        return SendMessageResp(message_id=update.id)

    async def download_file(self, req: DownloadFileReq) -> DownloadFileResp:
        if not (
            message := await self._client.get_messages(
                chat_id=req.chat, message_ids=req.message_id
            )
        ) or not isinstance(message, t.Message):
            raise TechnicalError(
                f"Message with id {req.message_id} not found in chat {req.chat}"
            )

        if not message.document:
            raise UnDownloadableMessage(message.id)

        bytes_to_read = req.end - req.begin + 1

        async def chunks():
            rest = bytes_to_read

            if req.end < req.begin:
                raise TechnicalError(
                    f"Invalid range: end must be greater than or equal to begin, got begin={req.begin} end={req.end}"
                )

            if res := self._client.get_file(
                file_id=file_id.FileId.decode(message.document.file_id),
                offset=req.begin,
            ):
                async for chunk in res:
                    if len(chunk) > rest:
                        chunk = chunk[:rest]
                    yield chunk
                    rest -= len(chunk)
                    if rest <= 0:
                        break

        return DownloadFileResp(chunks=chunks(), size=bytes_to_read)

    async def resolve_channel_id(self, channel_id: str) -> int:
        try:
            return int(f"-100{channel_id}")
        except ValueError:
            if (
                channel := await self._client.resolve_peer(f"@{channel_id}")
            ) and isinstance(channel, t.PeerChannel):
                return channel.channel_id
            raise TechnicalError(f"Invalid channel id {channel_id}")

    async def _get_me(self) -> GetMeResp:
        me = await self._client.get_me()
        return GetMeResp(
            name=(
                f"@{me.username}"
                if me.username
                else f"{me.first_name} {me.last_name or ''}".strip()
            ),
            is_premium=bool(me.is_premium),
        )


class Session:
    def __init__(self, session_file: str):
        self.session_file = session_file

    def get(self) -> Optional[str]:
        if os.path.exists(self.session_file):
            with open(self.session_file, "r") as f:
                return f.read().strip()
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


async def login_as_account(config: Config) -> Client:
    if not config.telegram.account:
        raise TechnicalError("Account configuration is missing")

    api_id = config.telegram.api_id
    api_hash = config.telegram.api_hash

    session = Session(config.telegram.account.session_file)
    if sess := session.get():
        client = Client(
            name="account", session_string=sess, api_id=api_id, api_hash=api_hash
        )
        await client.start()
    else:
        client = Client(
            name="account", api_id=api_id, api_hash=api_hash, in_memory=True
        )
        await client.start()
        session.save(await client.export_session_string())

    if (me := await client.get_me()) and isinstance(me, t.User) and me.username:
        logger.info(f"logged in as @{me.username}")
    else:
        logger.warning("logged in as account, but no username found")

    return client


async def login_as_bots(config: Config) -> List[Client]:
    api_id = config.telegram.api_id
    api_hash = config.telegram.api_hash

    bot_tokens = config.telegram.bot.tokens or [config.telegram.bot.token]

    async def login(token: str) -> Client:
        bot_id, _ = token.split(":")

        session = Session(
            os.path.join(config.telegram.bot.session_file, f"{bot_id}.session")
        )

        if sess := session.get():
            client = Client(
                name=bot_id, session_string=sess, api_id=api_id, api_hash=api_hash
            )
            await client.start()
        else:
            client = Client(
                name="tgfs",
                bot_token=token,
                api_id=api_id,
                api_hash=api_hash,
                in_memory=True,
            )
            await client.start()
            session.save_multibot(await client.export_session_string())

        if (me := await client.get_me()) and isinstance(me, t.User) and me.username:
            logger.info(f"logged in as @{me.username}")
        else:
            logger.warning("logged in as bot, but no username found")

        return client

    return await asyncio.gather(*(login(token) for token in bot_tokens))
