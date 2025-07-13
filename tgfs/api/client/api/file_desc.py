from typing import AsyncIterator, Optional

from tgfs.api.client.api.model import (
    FileDescAPIResponse,
    FileMessageEmpty,
    GeneralFileMessage,
)
from tgfs.api.client.repository.impl.file import FileRepository
from tgfs.api.client.repository.interface import IFDRepository
from tgfs.model.directory import TGFSFileRef
from tgfs.model.file import TGFSFile, TGFSFileVersion


class FileDescApi:
    def __init__(self, fd_repo: IFDRepository, file_repo: FileRepository):
        self.__fd_repo = fd_repo
        self.__file_repo = file_repo

    async def create_file_desc(
        self, file_msg: GeneralFileMessage
    ) -> FileDescAPIResponse:
        return await self.append_file_version(file_msg, fr=None)

    async def get_file_desc(self, fr: TGFSFileRef) -> TGFSFile:
        return await self.__fd_repo.get(fr)

    async def download_file_at_version(
        self, as_name: str, version: TGFSFileVersion, begin: int, end: int
    ) -> AsyncIterator[bytes]:
        return await self.__file_repo.download_file(
            name=as_name, message_id=version.message_id, begin=begin, end=end
        )

    async def append_file_version(
        self, file_msg: GeneralFileMessage, fr: Optional[TGFSFileRef] = None
    ) -> FileDescAPIResponse:
        fd = await self.get_file_desc(fr) if fr else TGFSFile(name=file_msg.name)

        if isinstance(file_msg, FileMessageEmpty):
            fd.add_empty_version()
        else:
            sent_file_msg = await self.__file_repo.save(file_msg)
            fd.add_version_from_sent_file_message(sent_file_msg)

        return await self.__fd_repo.save(fd, fr)

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

        return await self.__fd_repo.save(fd, fr)

    async def delete_file_version(
        self, fr: TGFSFileRef, version_id: str
    ) -> FileDescAPIResponse:
        fd = await self.get_file_desc(fr)
        fd.delete_version(version_id)
        return await self.__fd_repo.save(fd, fr)
