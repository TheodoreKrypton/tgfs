import json
import logging
from typing import Optional

from tgfs.api.client.api.message import MessageApi
from tgfs.api.client.api.model import FileDescAPIResponse
from tgfs.api.client.repository.interface import IFDRepository
from tgfs.errors.telegram import MessageNotFound
from tgfs.model.directory import TGFSFileRef
from tgfs.model.file import TGFSFile

logger = logging.getLogger(__name__)


class TGMsgFDRepository(IFDRepository):
    def __init__(self, message_api: MessageApi):
        self.__message_api = message_api

    async def save(
        self, fd: TGFSFile, fr: Optional[TGFSFileRef] = None
    ) -> FileDescAPIResponse:
        # If file referer is None, create a new file descriptor message.
        if fr is None:
            return FileDescAPIResponse(
                message_id=await self.__message_api.send_text(fd.to_json()),
                fd=fd,
            )

        # If file referer is provided, try to update the existing file descriptor.
        # But if the message is not found (probably got deleted manually), a new file descriptor will be created.
        try:
            return FileDescAPIResponse(
                message_id=await self.__message_api.edit_message_text(
                    message_id=fr.message_id, message=fd.to_json()
                ),
                fd=fd,
            )
        except MessageNotFound:
            return await self.save(fd)

    async def get(self, fr: TGFSFileRef) -> TGFSFile:
        message = (await self.__message_api.get_messages([fr.message_id]))[0]

        empty = TGFSFile.empty(fr.name)

        if not message:
            logging.error(
                f"File descriptor (message_id: {fr.message_id}) for {fr.name} not found"
            )
            return empty

        fd = TGFSFile.from_dict(json.loads(message.text))

        versions = fd.get_versions(exclude_empty=True)
        file_messages = await self.__message_api.get_messages(
            [version.message_id for version in versions if version.message_id]
        )

        for i, version in enumerate(versions):
            if (file_message := file_messages[i]) and file_message.document:
                version.size = file_message.document.size
            else:
                logger.warning(
                    f"File message for version {version.id} of {fr.name} not found"
                )
                version.set_invalid()

        return fd if versions else empty
