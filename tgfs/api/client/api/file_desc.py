from typing import AsyncIterator

from tgfs.api.client.repository.impl.file import FileRepository
from tgfs.api.client.repository.interface import IFDRepository
from tgfs.api.client.api.model import GeneralFileMessage, FileMessageEmpty
from tgfs.api.client.api.model import FileDescAPIResponse
from tgfs.model.file import TGFSFile, TGFSFileVersion
from tgfs.model.directory import TGFSFileRef


class FileDescApi:
    def __init__(self, fd_repo: IFDRepository, file_repo: FileRepository):
        self.__fd_repo = fd_repo
        self.__file_repo = file_repo

    async def create_file_desc(
        self, file_msg: GeneralFileMessage
    ) -> FileDescAPIResponse:
        fd = TGFSFile(name=file_msg.name)

        if isinstance(file_msg, FileMessageEmpty):
            fd.add_empty_version()
        else:
            sent_file_msg = await self.__file_repo.save(file_msg)
            fd.add_version_from_sent_file_message(sent_file_msg)

        return await self.__fd_repo.save(fd=fd)

    async def get_file_desc(self, fr: TGFSFileRef) -> TGFSFile:
        return await self.__fd_repo.get(fr=fr)

    async def download_file_at_version(
        self, as_name: str, version: TGFSFileVersion
    ) -> AsyncIterator[bytes]:
        return await self.__file_repo.download_file(
            name=as_name, message_id=version.message_id
        )

    async def add_file_version(
        self, fr: TGFSFileRef, file_msg: GeneralFileMessage
    ) -> FileDescAPIResponse:
        fd = await self.get_file_desc(fr)

        if isinstance(file_msg, FileMessageEmpty):
            fd.add_empty_version()
        else:
            sent_file_msg = await self.__file_repo.save(file_msg)
            fd.add_version_from_sent_file_message(sent_file_msg)

        await self.__fd_repo.save(fd=fd, message_id=fr.message_id)
        return FileDescAPIResponse(message_id=fr.message_id, fd=fd)

    async def update_file_version(
        self, fr: TGFSFileRef, file_msg: GeneralFileMessage, version_id: str
    ) -> FileDescAPIResponse:
        fd = await self.get_file_desc(fr)
        if isinstance(file_msg, FileMessageEmpty):
            fv = fd.get_version(version_id)
            fv.set_invalid()
            fd.update_version(fv)
        else:
            sent_file_msg = await self.__file_repo.save(file_msg)
            fv = fd.get_version(version_id)
            fv.message_id = sent_file_msg.message_id
            fv.size = sent_file_msg.size
            fd.update_version(fv)

        await self.__fd_repo.save(fd=fd, message_id=fr.message_id)
        return FileDescAPIResponse(message_id=fr.message_id, fd=fd)

    async def delete_file_version(
        self, fr: TGFSFileRef, version_id: str
    ) -> FileDescAPIResponse:
        fd = await self.get_file_desc(fr)
        fd.delete_version(version_id)
        await self.__fd_repo.save(fd=fd, message_id=fr.message_id)
        return FileDescAPIResponse(message_id=fr.message_id, fd=fd)
