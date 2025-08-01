import os
from typing import Optional

from tgfs.core.model import TGFSDirectory, TGFSFileDesc, TGFSFileRef, TGFSFileVersion
from tgfs.errors import FileOrDirectoryDoesNotExist
from tgfs.reqres import FileContent, FileMessageEmpty, GeneralFileMessage
from tgfs.tasks import create_download_task, create_upload_task

from .file_desc import FileDescApi
from .metadata import MetaDataApi


class FileApi:
    def __init__(self, metadata_api: MetaDataApi, file_desc_api: FileDescApi):
        self.__metadata_api = metadata_api
        self.__file_desc_api = file_desc_api

    async def copy(
        self, where: TGFSDirectory, fr: TGFSFileRef, name: Optional[str] = None
    ) -> TGFSFileRef:
        copied_fr = where.create_file_ref(name or fr.name, fr.message_id)
        await self.__metadata_api.push()
        return copied_fr

    async def __create(
        self, where: TGFSDirectory, file_msg: GeneralFileMessage
    ) -> TGFSFileDesc:
        resp = await self.__file_desc_api.create_file_desc(file_msg)
        where.create_file_ref(file_msg.name, file_message_id=resp.message_id)
        await self.__metadata_api.push()
        return resp.fd

    async def __update_file_ref_message_id_if_necessary(
        self, fr: TGFSFileRef, message_id: int
    ) -> None:
        """
        This method is called to update the message_id if the original message of the
        message_id marked in the metadata is missing (e.g. the message was manually deleted).
        """
        if fr.message_id != message_id:
            fr.message_id = message_id
            await self.__metadata_api.push()

    async def __update(
        self, fr: TGFSFileRef, file_msg: GeneralFileMessage, version_id: Optional[str]
    ) -> TGFSFileDesc:
        if version_id:
            resp = await self.__file_desc_api.update_file_version(
                fr, file_msg, version_id
            )
        else:
            resp = await self.__file_desc_api.append_file_version(file_msg, fr)
        await self.__update_file_ref_message_id_if_necessary(fr, resp.message_id)
        return resp.fd

    async def rm(self, fr: TGFSFileRef, version_id: Optional[str] = None) -> None:
        if not version_id:
            fr.delete()
            await self.__metadata_api.push()
        else:
            resp = await self.__file_desc_api.delete_file_version(fr, version_id)
            await self.__update_file_ref_message_id_if_necessary(fr, resp.message_id)

    async def upload(
        self,
        under: TGFSDirectory,
        file_msg: GeneralFileMessage,
        version_id: Optional[str] = None,
    ) -> TGFSFileDesc:
        try:
            if not isinstance(file_msg, FileMessageEmpty):
                file_msg.task_tracker = await create_upload_task(
                    os.path.join(under.absolute_path, file_msg.name),
                    file_msg.get_size(),
                )
            try:
                fr = under.find_file(file_msg.name)
                res = await self.__update(fr, file_msg, version_id)
            except FileOrDirectoryDoesNotExist:
                res = await self.__create(under, file_msg)

            if file_msg.task_tracker:
                await file_msg.task_tracker.mark_completed()
            return res
        except Exception as ex:
            if file_msg.task_tracker:
                await file_msg.task_tracker.mark_failed(str(ex))
            raise ex

    async def desc(self, fr: TGFSFileRef) -> TGFSFileDesc:
        return await self.__file_desc_api.get_file_desc(fr)

    async def retrieve(
        self,
        fr: TGFSFileRef,
        begin: int,
        end: int,
        as_name: str,
    ) -> FileContent:
        fd = await self.desc(fr)
        if isinstance(fd, FileMessageEmpty):

            async def empty_file() -> FileContent:
                yield b""

            return empty_file()
        fv = fd.get_latest_version()

        task_tracker = await create_download_task(
            os.path.join(fr.location.absolute_path, as_name or fr.name),
            file_size=fv.size,
        )

        async def chunks():
            size_processed = 0

            try:
                async for chunk in await self.__file_desc_api.download_file_at_version(
                    fv, begin, end, as_name or fr.name
                ):
                    size_processed += len(chunk)
                    await task_tracker.update_progress(size_processed=size_processed)
                    yield chunk

                await task_tracker.mark_completed()
            except Exception as ex:
                await task_tracker.mark_failed(str(ex))
                raise ex

        return chunks()

    async def retrieve_version(
        self,
        fv: TGFSFileVersion,
        begin: int,
        end: int,
        as_name: str,
    ) -> FileContent:
        return await self.__file_desc_api.download_file_at_version(
            fv,
            begin,
            end,
            as_name,
        )
