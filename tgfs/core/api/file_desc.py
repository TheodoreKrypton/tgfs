from typing import Optional

from tgfs.core.model import TGFSFileDesc, TGFSFileRef, TGFSFileVersion
from tgfs.core.repository.interface import (
    FDRepositoryResp,
    IFDRepository,
    IFileContentRepository,
)
from tgfs.reqres import FileContent, FileMessageEmpty, GeneralFileMessage


class FileDescApi:
    def __init__(self, fd_repo: IFDRepository, fc_repo: IFileContentRepository):
        self.__fd_repo = fd_repo
        self.__fc_repo = fc_repo

    async def create_file_desc(self, file_msg: GeneralFileMessage) -> FDRepositoryResp:
        return await self.append_file_version(file_msg, fr=None)

    async def get_file_desc(self, fr: TGFSFileRef) -> TGFSFileDesc:
        return await self.__fd_repo.get(fr)

    async def download_file_at_version(
        self, fv: TGFSFileVersion, begin: int, end: int, as_name: str
    ) -> FileContent:
        return await self.__fc_repo.get(
            fv=fv,
            begin=begin,
            end=end,
            name=as_name,
        )

    async def append_file_version(
        self, file_msg: GeneralFileMessage, fr: Optional[TGFSFileRef] = None
    ) -> FDRepositoryResp:
        fd = await self.get_file_desc(fr) if fr else TGFSFileDesc(name=file_msg.name)

        if isinstance(file_msg, FileMessageEmpty):
            fd.add_empty_version()
        else:
            sent_file_msg = await self.__fc_repo.save(file_msg)
            fd.add_version_from_sent_file_message(sent_file_msg)

        return await self.__fd_repo.save(fd, fr)

    async def update_file_version(
        self, fr: TGFSFileRef, file_msg: GeneralFileMessage, version_id: str
    ) -> FDRepositoryResp:
        fd = await self.get_file_desc(fr)
        if isinstance(file_msg, FileMessageEmpty):
            fv = fd.get_version(version_id)
            fv.set_invalid()
            fd.update_version(version_id, fv)
        else:
            sent_file_msg = await self.__fc_repo.save(file_msg)
            fv = TGFSFileVersion.from_sent_file_message(sent_file_msg)
            fv.id = version_id
            fd.update_version(version_id, fv)

        return await self.__fd_repo.save(fd, fr)

    async def delete_file_version(
        self, fr: TGFSFileRef, version_id: str
    ) -> FDRepositoryResp:
        fd = await self.get_file_desc(fr)
        fd.delete_version(version_id)
        return await self.__fd_repo.save(fd, fr)
