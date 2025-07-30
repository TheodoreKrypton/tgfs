import json
import logging
from typing import Optional
from itertools import chain

from tgfs.core.api import MessageApi
from tgfs.core.model import TGFSFileDesc, TGFSFileRef
from tgfs.core.repository.interface import (
    FDRepositoryResp,
    IFDRepository,
)
from tgfs.errors import MessageNotFound

logger = logging.getLogger(__name__)


class TGMsgFDRepository(IFDRepository):
    def __init__(self, message_api: MessageApi):
        self.__message_api = message_api

    async def save(
        self, fd: TGFSFileDesc, fr: Optional[TGFSFileRef] = None
    ) -> FDRepositoryResp:
        # If file_content referer is None, create a new file_content descriptor message.
        if fr is None:
            return FDRepositoryResp(
                message_id=await self.__message_api.send_text(fd.to_json()),
                fd=fd,
            )

        # If file_content referer is provided, try to update the existing file_content descriptor.
        # But if the message is not found (probably got deleted manually), a new file_content descriptor will be created.
        try:
            return FDRepositoryResp(
                message_id=await self.__message_api.edit_message_text(
                    message_id=fr.message_id, message=fd.to_json()
                ),
                fd=fd,
            )
        except MessageNotFound:
            return await self.save(fd)

    async def _validate_fv(
        self, fd: TGFSFileDesc, include_all_versions: bool
    ) -> TGFSFileDesc:
        versions = fd.get_versions(exclude_invalid=True)

        # Files in the channel may be deleted manually, so we need to check if the messages for the versions exist.

        file_messages = await self.__message_api.get_messages(
            list(chain(*(version.message_ids for version in versions)))
        )

        message_map = {msg.message_id: msg for msg in file_messages if msg}

        has_valid_version = False

        for i, version in enumerate(versions):
            for j, message_id in enumerate(version.message_ids):
                if (
                    not (file_message := message_map.get(message_id, None))
                    or not file_message.document
                ):
                    logger.warning(
                        f"File message {message_id} for part {j + 1} of {fd.name}@{version.id} not found"
                    )
                    version.set_invalid()
                    break
                version.part_sizes.append(file_message.document.size)
            if version.is_valid():
                has_valid_version = True
                if not include_all_versions:
                    # Found a valid version, no need to check further
                    return fd

        return fd if has_valid_version else TGFSFileDesc.empty(fd.name)

    async def get(
        self, fr: TGFSFileRef, include_all_versions: bool = False
    ) -> TGFSFileDesc:
        message = (await self.__message_api.get_messages([fr.message_id]))[0]

        if not message:
            logging.error(
                f"File descriptor (message_id: {fr.message_id}) for {fr.name} not found"
            )
            return TGFSFileDesc.empty(fr.name)

        fd = TGFSFileDesc.from_dict(json.loads(message.text), name=fr.name)
        return await self._validate_fv(fd, include_all_versions)
