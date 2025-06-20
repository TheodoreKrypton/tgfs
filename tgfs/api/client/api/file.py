from typing import Optional, AsyncIterator

from tgfs.api.client.api.file_desc import FileDescApi
from tgfs.api.client.api.metadata import MetaDataApi
from tgfs.api.client.api.model import GeneralFileMessage, FileMessageEmpty
from tgfs.errors.path import FileOrDirectoryDoesNotExist
from tgfs.model.directory import TGFSDirectory, TGFSFileRef
from tgfs.model.file import TGFSFile, TGFSFileVersion
from tgfs.utils.validate_name import validate_name


class FileApi:
    def __init__(self, metadata_api: MetaDataApi, file_desc_api: FileDescApi):
        self.__metadata_api = metadata_api
        self.__file_desc_api = file_desc_api

    async def copy(
        self, where: TGFSDirectory, fr: TGFSFileRef, name: Optional[str] = None
    ) -> TGFSFileRef:
        copied_fr = where.create_file_ref(name or fr.name, fr.message_id)
        await self.__metadata_api.update()
        return copied_fr

    async def __create(
        self, where: TGFSDirectory, file_msg: GeneralFileMessage
    ) -> TGFSFile:
        validate_name(file_msg.name)
        resp = await self.__file_desc_api.create_file_desc(file_msg)
        where.create_file_ref(file_msg.name, file_message_id=resp.message_id)
        await self.__metadata_api.update()
        return resp.fd

    async def __update_file_ref_message_id_if_necessary(
        self, fr: TGFSFileRef, message_id: int
    ) -> None:
        if fr.message_id != message_id:
            fr.message_id = message_id
            await self.__metadata_api.update()

    async def __update(
        self, fr: TGFSFileRef, file_msg: GeneralFileMessage, version_id: Optional[str]
    ) -> TGFSFile:
        if version_id:
            resp = await self.__file_desc_api.update_file_version(
                fr, file_msg, version_id
            )
        else:
            resp = await self.__file_desc_api.add_file_version(fr, file_msg)
        await self.__update_file_ref_message_id_if_necessary(fr, resp.message_id)
        return resp.fd

    async def rm(self, fr: TGFSFileRef, version_id: Optional[str] = None) -> None:
        if not version_id:
            fr.delete()
            await self.__metadata_api.update()
        else:
            resp = await self.__file_desc_api.delete_file_version(fr, version_id)
            await self.__update_file_ref_message_id_if_necessary(fr, resp.message_id)

    async def upload(
        self,
        under: TGFSDirectory,
        file_msg: GeneralFileMessage,
        version_id: Optional[str] = None,
    ) -> TGFSFile:
        try:
            fr = under.find_file(file_msg.name)
            return await self.__update(fr, file_msg, version_id)
        except FileOrDirectoryDoesNotExist:
            return await self.__create(under, file_msg)

    async def desc(self, fr: TGFSFileRef) -> TGFSFile:
        return await self.__file_desc_api.get_file_desc(fr)

    async def retrieve(self, fr: TGFSFileRef, as_name: str) -> AsyncIterator[bytes]:
        fd = await self.desc(fr)
        if isinstance(fd, FileMessageEmpty):

            async def empty_file() -> AsyncIterator[bytes]:
                yield b""

            return empty_file()
        else:
            version = fd.get_latest_version()
            return await self.__file_desc_api.download_file_at_version(
                as_name or fr.name, version
            )

    async def retrieve_version(
        self, version: TGFSFileVersion, as_name: str
    ) -> AsyncIterator[bytes]:
        return await self.__file_desc_api.download_file_at_version(as_name, version)
