import os
import pytest
from unittest.mock import AsyncMock, Mock, patch
import datetime

from tgfs.core.api.file import FileApi
from tgfs.core.api.file_desc import FileDescApi
from tgfs.core.api.metadata import MetaDataApi
from tgfs.core.model import TGFSDirectory, TGFSFileDesc, TGFSFileRef, TGFSFileVersion
from tgfs.errors import FileOrDirectoryDoesNotExist
from tgfs.reqres import (
    FileMessage,
    FileMessageEmpty,
    FileMessageFromBuffer,
)


class TestFileApi:
    @pytest.fixture
    def mock_metadata_api(self) -> AsyncMock:
        return AsyncMock(spec=MetaDataApi)

    @pytest.fixture
    def mock_file_desc_api(self) -> AsyncMock:
        return AsyncMock(spec=FileDescApi)

    @pytest.fixture
    def file_api(self, mock_metadata_api, mock_file_desc_api) -> FileApi:
        return FileApi(mock_metadata_api, mock_file_desc_api)

    @pytest.fixture
    def sample_directory(self) -> TGFSDirectory:
        return TGFSDirectory.root_dir()

    @pytest.fixture
    def sample_file_ref(self, sample_directory) -> TGFSFileRef:
        return TGFSFileRef(
            message_id=123,
            name="test_file.txt",
            location=sample_directory
        )

    @pytest.fixture
    def sample_file_desc(self) -> TGFSFileDesc:
        # Create a mock TGFSFileDesc with necessary attributes
        file_desc = Mock(spec=TGFSFileDesc)
        file_desc.get_latest_version.return_value = TGFSFileVersion(
            id="v1",
            updated_at=datetime.datetime.now(),
            message_ids=[123],
            part_sizes=[1024]
        )
        return file_desc

    @pytest.fixture
    def sample_file_message(self) -> FileMessageFromBuffer:
        return FileMessageFromBuffer.new(
            buffer=b"test content",
            name="test_file.txt"
        )

    def test_init(self, mock_metadata_api, mock_file_desc_api):
        file_api = FileApi(mock_metadata_api, mock_file_desc_api)
        
        assert file_api._metadata_api == mock_metadata_api
        assert file_api._file_desc_api == mock_file_desc_api

    @pytest.mark.asyncio
    async def test_copy_with_custom_name(
        self, file_api, mock_metadata_api, sample_directory, sample_file_ref
    ):
        new_name = "copied_file.txt"
        sample_directory.create_file_ref = Mock(return_value=sample_file_ref)
        
        result = await file_api.copy(sample_directory, sample_file_ref, new_name)
        
        sample_directory.create_file_ref.assert_called_once_with(new_name, sample_file_ref.message_id)
        mock_metadata_api.push.assert_called_once()
        assert result == sample_file_ref

    @pytest.mark.asyncio
    async def test_copy_with_default_name(
        self, file_api, mock_metadata_api, sample_directory, sample_file_ref
    ):
        sample_directory.create_file_ref = Mock(return_value=sample_file_ref)
        
        result = await file_api.copy(sample_directory, sample_file_ref)
        
        sample_directory.create_file_ref.assert_called_once_with(
            sample_file_ref.name, sample_file_ref.message_id
        )
        mock_metadata_api.push.assert_called_once()
        assert result == sample_file_ref

    @pytest.mark.asyncio
    async def test_create_new_file(
        self, file_api, mock_metadata_api, mock_file_desc_api, sample_directory, sample_file_message
    ):
        mock_response = Mock()
        mock_response.message_id = 456
        mock_response.fd = Mock(spec=TGFSFileDesc)
        mock_file_desc_api.create_file_desc.return_value = mock_response
        sample_directory.create_file_ref = Mock()
        
        result = await file_api._create_new_file(sample_directory, sample_file_message)
        
        mock_file_desc_api.create_file_desc.assert_called_once_with(sample_file_message)
        sample_directory.create_file_ref.assert_called_once_with(
            sample_file_message.name, mock_response.message_id
        )
        mock_metadata_api.push.assert_called_once()
        assert result == mock_response.fd

    @pytest.mark.asyncio
    async def test_update_file_ref_message_id_if_necessary_no_update(
        self, file_api, mock_metadata_api, sample_file_ref
    ):
        current_message_id = sample_file_ref.message_id
        
        await file_api._update_file_ref_message_id_if_necessary(
            sample_file_ref, current_message_id
        )
        
        mock_metadata_api.push.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_file_ref_message_id_if_necessary_with_update(
        self, file_api, mock_metadata_api, sample_file_ref
    ):
        new_message_id = 999
        original_message_id = sample_file_ref.message_id
        
        await file_api._update_file_ref_message_id_if_necessary(
            sample_file_ref, new_message_id
        )
        
        assert sample_file_ref.message_id == new_message_id
        mock_metadata_api.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_file_with_version_id(
        self, file_api, mock_file_desc_api, sample_file_ref, sample_file_message
    ):
        version_id = "v2"
        mock_response = Mock()
        mock_response.message_id = sample_file_ref.message_id  # Same ID, no update needed
        mock_response.fd = Mock(spec=TGFSFileDesc)
        mock_file_desc_api.update_file_version.return_value = mock_response
        
        result = await file_api._update_existing_file(
            sample_file_ref, sample_file_message, version_id
        )
        
        mock_file_desc_api.update_file_version.assert_called_once_with(
            sample_file_ref, sample_file_message, version_id
        )
        mock_file_desc_api.append_file_version.assert_not_called()
        assert result == mock_response.fd

    @pytest.mark.asyncio
    async def test_update_existing_file_without_version_id(
        self, file_api, mock_file_desc_api, sample_file_ref, sample_file_message
    ):
        mock_response = Mock()
        mock_response.message_id = sample_file_ref.message_id  # Same ID, no update needed
        mock_response.fd = Mock(spec=TGFSFileDesc)
        mock_file_desc_api.append_file_version.return_value = mock_response
        
        result = await file_api._update_existing_file(
            sample_file_ref, sample_file_message, None
        )
        
        mock_file_desc_api.append_file_version.assert_called_once_with(
            sample_file_message, sample_file_ref
        )
        mock_file_desc_api.update_file_version.assert_not_called()
        assert result == mock_response.fd

    @pytest.mark.asyncio
    async def test_rm_without_version_id(
        self, file_api, mock_metadata_api, sample_file_ref
    ):
        sample_file_ref.delete = Mock()
        
        await file_api.rm(sample_file_ref)
        
        sample_file_ref.delete.assert_called_once()
        mock_metadata_api.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_rm_with_version_id(
        self, file_api, mock_file_desc_api, sample_file_ref
    ):
        version_id = "v1"
        mock_response = Mock()
        mock_response.message_id = sample_file_ref.message_id  # Same ID, no update needed
        mock_file_desc_api.delete_file_version.return_value = mock_response
        sample_file_ref.delete = Mock()
        
        await file_api.rm(sample_file_ref, version_id)
        
        mock_file_desc_api.delete_file_version.assert_called_once_with(
            sample_file_ref, version_id
        )
        sample_file_ref.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_non_uploadable_message_new_file(
        self, file_api, mock_file_desc_api, mock_metadata_api, sample_directory
    ):
        # Create a non-uploadable file message (regular FileMessage)
        file_msg = Mock(spec=FileMessage)
        file_msg.name = "test_file.txt"
        sample_directory.find_file = Mock(side_effect=FileOrDirectoryDoesNotExist("Not found"))
        
        mock_response = Mock()
        mock_response.message_id = 789
        mock_response.fd = Mock(spec=TGFSFileDesc)
        mock_file_desc_api.create_file_desc.return_value = mock_response
        sample_directory.create_file_ref = Mock()
        
        result = await file_api.upload(sample_directory, file_msg)
        
        sample_directory.find_file.assert_called_once_with(file_msg.name)
        mock_file_desc_api.create_file_desc.assert_called_once_with(file_msg)
        sample_directory.create_file_ref.assert_called_once_with(file_msg.name, 789)
        mock_metadata_api.push.assert_called_once()
        assert result == mock_response.fd

    @pytest.mark.asyncio
    async def test_upload_non_uploadable_message_existing_file(
        self, file_api, mock_file_desc_api, sample_directory, sample_file_ref
    ):
        # Create a non-uploadable file message (regular FileMessage)
        file_msg = Mock(spec=FileMessage)
        file_msg.name = "test_file.txt"
        sample_directory.find_file = Mock(return_value=sample_file_ref)
        
        mock_response = Mock()
        mock_response.message_id = sample_file_ref.message_id  # Same ID, no update needed
        mock_response.fd = Mock(spec=TGFSFileDesc)
        mock_file_desc_api.append_file_version.return_value = mock_response
        
        result = await file_api.upload(sample_directory, file_msg)
        
        sample_directory.find_file.assert_called_once_with(file_msg.name)
        mock_file_desc_api.append_file_version.assert_called_once_with(file_msg, sample_file_ref)
        assert result == mock_response.fd

    @pytest.mark.asyncio
    @patch('tgfs.core.api.file.create_upload_task')
    async def test_upload_uploadable_message_success(
        self, mock_create_task, file_api, mock_file_desc_api, mock_metadata_api, sample_directory, sample_file_message
    ):
        # Mock the task tracker
        mock_task_tracker = AsyncMock()
        mock_task_tracker.mark_completed = AsyncMock()
        mock_create_task.return_value = mock_task_tracker
        
        # Mock directory behavior for new file creation
        sample_directory.find_file = Mock(side_effect=FileOrDirectoryDoesNotExist("Not found"))
        sample_directory.create_file_ref = Mock()
        
        mock_response = Mock()
        mock_response.message_id = 789
        mock_response.fd = Mock(spec=TGFSFileDesc)
        mock_file_desc_api.create_file_desc.return_value = mock_response
        
        # Mock absolute_path property
        with patch.object(type(sample_directory), 'absolute_path', new="/test/path"):
            result = await file_api.upload(sample_directory, sample_file_message)
            
            # Verify task creation
            mock_create_task.assert_called_once_with(
                os.path.join("/test/path", sample_file_message.name),
                sample_file_message.get_size()
            )
            
            # Verify task tracker was assigned and marked completed
            assert sample_file_message.task_tracker == mock_task_tracker
            mock_task_tracker.mark_completed.assert_called_once()
            
            # Verify file creation
            sample_directory.find_file.assert_called_once_with(sample_file_message.name)
            mock_file_desc_api.create_file_desc.assert_called_once_with(sample_file_message)
            assert result == mock_response.fd

    @pytest.mark.asyncio
    @patch('tgfs.core.api.file.create_upload_task')
    async def test_upload_uploadable_message_failure(
        self, mock_create_task, file_api, mock_file_desc_api, sample_directory, sample_file_message
    ):
        # Mock the task tracker
        mock_task_tracker = AsyncMock()
        mock_task_tracker.mark_failed = AsyncMock()
        mock_create_task.return_value = mock_task_tracker
        
        # Mock directory behavior for new file creation
        sample_directory.find_file = Mock(side_effect=FileOrDirectoryDoesNotExist("Not found"))
        
        # Mock file creation failure
        test_exception = Exception("Upload failed")
        mock_file_desc_api.create_file_desc.side_effect = test_exception
        
        # Mock absolute_path property
        with patch.object(type(sample_directory), 'absolute_path', new="/test/path"):
            with pytest.raises(Exception, match="Upload failed"):
                await file_api.upload(sample_directory, sample_file_message)
        
        # Verify task tracker was assigned and marked as failed
        assert sample_file_message.task_tracker == mock_task_tracker
        mock_task_tracker.mark_failed.assert_called_once_with("Upload failed")

    @pytest.mark.asyncio
    async def test_desc(self, file_api, mock_file_desc_api, sample_file_ref, sample_file_desc):
        mock_file_desc_api.get_file_desc.return_value = sample_file_desc
        
        result = await file_api.desc(sample_file_ref)
        
        mock_file_desc_api.get_file_desc.assert_called_once_with(sample_file_ref)
        assert result == sample_file_desc

    @pytest.mark.asyncio
    async def test_retrieve_empty_file(self, file_api, mock_file_desc_api, sample_file_ref):
        # Mock an empty file descriptor
        empty_file_desc = FileMessageEmpty.new(name="empty.txt")
        mock_file_desc_api.get_file_desc.return_value = empty_file_desc
        
        result = await file_api.retrieve(sample_file_ref, 0, -1, "empty.txt")
        
        # Test that the result is an async generator that yields empty bytes
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        assert chunks == [b""]
        mock_file_desc_api.get_file_desc.assert_called_once_with(sample_file_ref)

    @pytest.mark.asyncio
    async def test_retrieve_regular_file(self, file_api, mock_file_desc_api, sample_file_ref, sample_file_desc):
        mock_file_desc_api.get_file_desc.return_value = sample_file_desc
        
        # Mock the download method
        async def mock_download_chunks():
            yield b"chunk1"
            yield b"chunk2"
        
        mock_file_desc_api.download_file_at_version.return_value = mock_download_chunks()
        
        result = await file_api.retrieve(sample_file_ref, 0, 100, "test.txt")
        
        # Test that the result yields the expected chunks
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        assert chunks == [b"chunk1", b"chunk2"]
        mock_file_desc_api.get_file_desc.assert_called_once_with(sample_file_ref)
        mock_file_desc_api.download_file_at_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_with_exception(self, file_api, mock_file_desc_api, sample_file_ref, sample_file_desc):
        mock_file_desc_api.get_file_desc.return_value = sample_file_desc
        
        # Mock the download method to raise an exception
        async def mock_download_chunks():
            raise Exception("Download failed")
            yield  # This will never execute
        
        mock_file_desc_api.download_file_at_version.return_value = mock_download_chunks()
        
        result = await file_api.retrieve(sample_file_ref, 0, 100, "test.txt")
        
        # Test that the exception is propagated
        with pytest.raises(Exception, match="Download failed"):
            async for chunk in result:
                pass

    @pytest.mark.asyncio
    async def test_retrieve_with_default_name(self, file_api, mock_file_desc_api, sample_file_ref, sample_file_desc):
        mock_file_desc_api.get_file_desc.return_value = sample_file_desc
        
        # Mock the download method
        async def mock_download_chunks():
            yield b"data"
        
        mock_file_desc_api.download_file_at_version.return_value = mock_download_chunks()
        
        result = await file_api.retrieve(sample_file_ref, 0, 100, None)
        
        # Consume the iterator to trigger the call
        async for chunk in result:
            pass
        
        # Verify the call was made with the file_ref name as default
        call_args = mock_file_desc_api.download_file_at_version.call_args[0]
        assert call_args[3] == sample_file_ref.name  # as_name parameter

    @pytest.mark.asyncio
    async def test_retrieve_version(self, file_api, mock_file_desc_api):
        file_version = TGFSFileVersion(
            id="v1",
            updated_at=datetime.datetime.now(),
            message_ids=[123],
            part_sizes=[1024]
        )
        as_name = "version_file.txt"
        begin, end = 0, 500
        
        # Mock the download method
        async def mock_download_chunks():
            yield b"version_data"
        
        mock_file_desc_api.download_file_at_version.return_value = mock_download_chunks()
        
        result = await file_api.retrieve_version(file_version, begin, end, as_name)
        
        # Test that the result yields the expected chunks
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        assert chunks == [b"version_data"]
        mock_file_desc_api.download_file_at_version.assert_called_once_with(
            file_version, begin, end, as_name
        )

    @pytest.mark.asyncio
    async def test_upload_with_version_id(
        self, file_api, mock_file_desc_api, sample_directory, sample_file_ref, sample_file_message
    ):
        version_id = "v3"
        sample_directory.find_file = Mock(return_value=sample_file_ref)
        
        mock_response = Mock()
        mock_response.message_id = sample_file_ref.message_id  # Same ID, no update needed
        mock_response.fd = Mock(spec=TGFSFileDesc)
        mock_file_desc_api.update_file_version.return_value = mock_response
        
        result = await file_api.upload(sample_directory, sample_file_message, version_id)
        
        sample_directory.find_file.assert_called_once_with(sample_file_message.name)
        mock_file_desc_api.update_file_version.assert_called_once_with(
            sample_file_ref, sample_file_message, version_id
        )
        assert result == mock_response.fd

    @pytest.mark.asyncio
    async def test_rm_with_version_id_message_id_update(
        self, file_api, mock_metadata_api, mock_file_desc_api, sample_file_ref
    ):
        version_id = "v1"
        new_message_id = 999
        mock_response = Mock()
        mock_response.message_id = new_message_id  # Different ID, update needed
        mock_file_desc_api.delete_file_version.return_value = mock_response
        original_message_id = sample_file_ref.message_id
        
        await file_api.rm(sample_file_ref, version_id)
        
        mock_file_desc_api.delete_file_version.assert_called_once_with(
            sample_file_ref, version_id
        )
        # Verify message_id was updated
        assert sample_file_ref.message_id == new_message_id
        mock_metadata_api.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_file_message_id_update(
        self, file_api, mock_metadata_api, mock_file_desc_api, sample_file_ref, sample_file_message
    ):
        new_message_id = 888
        mock_response = Mock()
        mock_response.message_id = new_message_id  # Different ID, update needed
        mock_response.fd = Mock(spec=TGFSFileDesc)
        mock_file_desc_api.append_file_version.return_value = mock_response
        original_message_id = sample_file_ref.message_id
        
        result = await file_api._update_existing_file(
            sample_file_ref, sample_file_message, None
        )
        
        mock_file_desc_api.append_file_version.assert_called_once_with(
            sample_file_message, sample_file_ref
        )
        # Verify message_id was updated
        assert sample_file_ref.message_id == new_message_id
        mock_metadata_api.push.assert_called_once()
        assert result == mock_response.fd