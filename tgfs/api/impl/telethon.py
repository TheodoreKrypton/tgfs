import os
from typing import Optional
from getpass import getpass

from telethon import TelegramClient, types as tlt, functions as tlf
from telethon.sessions import StringSession
from telethon.tl.types import InputDocumentFileLocation
from telethon.errors import SessionPasswordNeededError

from tgfs.api.interface import ITDLibClient
from tgfs.api.types import (
    GetMessagesReq,
    GetMessagesResp,
    GetPinnedMessageReq,
    MessageResp,
    Document,
    SendTextReq,
    SendMessageResp,
    EditMessageTextReq,
    EditMessageMediaReq,
    Message,
    SearchMessageReq,
    PinMessageReq,
    SaveBigFilePartReq,
    SaveFilePartResp,
    SaveFilePartReq,
    SendFileReq,
    DownloadFileReq,
    DownloadFileResp,
)
from tgfs.config import Config


class TelethonAPI(ITDLibClient):
    def __init__(self, client: TelegramClient):
        self._client = client

    @staticmethod
    def __transform_messages(messages: list[tlt.Message]) -> GetMessagesResp:
        res = GetMessagesResp()

        for m in messages:
            if not m:
                continue

            obj = MessageResp(
                message_id=m.id,
                text="",
                document=None,
            )

            if m.message:
                obj.text = m.message

            if m.media and (doc := m.media.document):
                obj.document = Document(
                    size=doc.size,
                    id=doc.id,
                    access_hash=doc.access_hash,
                    file_reference=doc.file_reference,
                )

            res.append(obj)
        return res

    async def get_messages(self, req: GetMessagesReq) -> GetMessagesResp:
        messages = await self._client.get_messages(
            entity=req.chat_id, ids=req.message_ids
        )
        return self.__transform_messages(messages)

    async def send_text(self, req: SendTextReq) -> SendMessageResp:
        message = await self._client.send_message(entity=req.chat_id, message=req.text)
        return SendMessageResp(message_id=message.id)

    async def edit_message_text(self, req: EditMessageTextReq) -> SendMessageResp:
        message = await self._client.edit_message(
            entity=req.chat_id, message=req.message_id, text=req.text
        )
        return SendMessageResp(message_id=message.id)

    async def edit_message_media(self, req: EditMessageMediaReq) -> Message:
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

    async def search_messages(self, req: SearchMessageReq) -> GetMessagesResp:
        messages = await self._client.get_messages(
            entity=req.chat_id, search=req.search
        )
        return self.__transform_messages(messages)

    async def get_pinned_messages(self, req: GetPinnedMessageReq) -> GetMessagesResp:
        messages = await self._client.get_messages(
            entity=req.chat_id, filter=tlt.InputMessagesFilterPinned()
        )
        return self.__transform_messages(messages)

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
        file = tlt.InputFile(
            id=req.file.id,
            parts=req.file.parts,
            name=req.file.name,
            md5_checksum="",
        )
        message = await self._client.send_file(
            entity=req.chat_id, file=file, caption=req.caption, force_document=True
        )
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
        return SendMessageResp(message_id=message.id)

    async def download_file(self, req: DownloadFileReq) -> DownloadFileResp:
        message = await self._client.get_messages(
            entity=req.chat_id, ids=req.message_id
        )

        chunk_size = req.chunk_size * 1024

        async def chunks():
            async for chunk in self._client.iter_download(
                file=InputDocumentFileLocation(
                    id=message.media.document.id,
                    access_hash=message.media.document.access_hash,
                    file_reference=message.media.document.file_reference,
                    thumb_size="",
                ),
                request_size=chunk_size,
            ):
                yield chunk

        return DownloadFileResp(chunks=chunks(), size=message.media.document.size)


class Session:
    def __init__(self, session_file: str):
        self.session_file = session_file

    def get(self) -> Optional[StringSession]:
        if os.path.exists(self.session_file):
            with open(self.session_file, "r") as f:
                return StringSession(f.read().strip())
        return None

    def save(self, session_string: str):
        with open(self.session_file, "w") as f:
            f.write(session_string)


async def login_as_account(config: Config) -> TelegramClient:
    api_id = config.telegram.api_id
    api_hash = config.telegram.api_hash

    session = Session(config.telegram.account.session_file)
    if sess := session.get():
        client = TelegramClient(sess, api_id, api_hash)
        await client.connect()
        return client

    phone_number = input("Phone Number: ")
    client = TelegramClient(StringSession(), api_id, api_hash)
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

    session.save(client.session.save())

    return client


async def login_as_bot(config: Config) -> TelegramClient:
    api_id = config.telegram.api_id
    api_hash = config.telegram.api_hash

    session = Session(config.telegram.bot.session_file)
    if sess := session.get():
        client = TelegramClient(sess, api_id, api_hash)
        await client.connect()
        return client

    client = await TelegramClient(StringSession(), api_id, api_hash).start(
        bot_token=config.telegram.bot.token
    )
    session.save(client.session.save())
    return client
