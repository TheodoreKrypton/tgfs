import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import AsyncIterator

from tgfs.core.ops import Ops
from tgfs.core.client import Client
from tgfs.core.model import TGFSDirectory, TGFSFileRef, TGFSFileDesc
from tgfs.errors import FileOrDirectoryDoesNotExist, InvalidPath
from tgfs.reqres import (
    FileMessageEmpty, FileMessageFromBuffer, FileMessageFromPath,
    FileMessageFromStream, FileMessageImported, MessageRespWithDocument
)


class TestOps:
    @pytest.fixture
    def mock_client(self):
        client = Mock(spec=Client)
        client.dir_api = Mock()
        client.file_api = Mock()
        client.message_api = Mock()
        return client

    @pytest.fixture
    def mock_root_directory(self):
        root = Mock(spec=TGFSDirectory)
        root.parent = None
        return root

    @pytest.fixture
    def ops_instance(self, mock_client, mock_root_directory):
        mock_client.dir_api.root = mock_root_directory
        return Ops(mock_client)

    def test_init(self, mock_client):
        ops = Ops(mock_client)
        assert ops._client == mock_client

    def test_validate_path_valid(self, ops_instance):
        # Valid paths should not raise exceptions
        ops_instance._validate_path("/valid/path")
        ops_instance._validate_path("/file.txt")
        ops_instance._validate_path("/a")

    def test_validate_path_invalid_trailing_slash(self, ops_instance):
        with pytest.raises(InvalidPath):
            ops_instance._validate_path("/invalid/path/")

    def test_validate_path_invalid_no_leading_slash(self, ops_instance):
        with pytest.raises(InvalidPath):
            ops_instance._validate_path("invalid/path")

    def test_cd_root(self, ops_instance, mock_root_directory):
        result = ops_instance.cd("/")
        assert result == mock_root_directory

    def test_cd_single_directory(self, ops_instance, mock_root_directory):
        mock_subdir = Mock(spec=TGFSDirectory)
        mock_root_directory.find_dir.return_value = mock_subdir
        
        result = ops_instance.cd("/subdir")
        
        mock_root_directory.find_dir.assert_called_once_with("subdir")
        assert result == mock_subdir

    def test_cd_nested_directories(self, ops_instance, mock_root_directory):
        mock_subdir1 = Mock(spec=TGFSDirectory)
        mock_subdir2 = Mock(spec=TGFSDirectory)
        
        mock_root_directory.find_dir.return_value = mock_subdir1
        mock_subdir1.find_dir.return_value = mock_subdir2
        
        result = ops_instance.cd("/dir1/dir2")
        
        mock_root_directory.find_dir.assert_called_with("dir1")
        mock_subdir1.find_dir.assert_called_with("dir2")
        assert result == mock_subdir2

    def test_cd_with_parent_directory(self, ops_instance, mock_root_directory):
        mock_subdir1 = Mock(spec=TGFSDirectory)
        mock_subdir2 = Mock(spec=TGFSDirectory)
        mock_parent = Mock(spec=TGFSDirectory)
        
        # Set up proper parent chain
        mock_subdir2.parent = mock_parent
        mock_subdir1.parent = mock_root_directory
        
        # Configure find_dir to return the correct subdirectories in sequence
        def find_dir_side_effect(name):
            if name == "dir1":
                return mock_subdir1
            elif name == "dir2":
                return mock_subdir2
            else:
                raise FileOrDirectoryDoesNotExist(name)
        
        mock_root_directory.find_dir.side_effect = find_dir_side_effect
        mock_subdir1.find_dir.side_effect = find_dir_side_effect
        
        result = ops_instance.cd("/dir1/dir2/..")
        
        # Should navigate to dir1/dir2 then go back to parent
        assert result == mock_parent

    def test_cd_with_current_directory(self, ops_instance, mock_root_directory):
        mock_subdir = Mock(spec=TGFSDirectory)
        mock_root_directory.find_dir.return_value = mock_subdir
        
        result = ops_instance.cd("/subdir/.")
        
        mock_root_directory.find_dir.assert_called_once_with("subdir")
        assert result == mock_subdir

    def test_ls_directory(self, ops_instance, mock_root_directory):
        mock_subdir = Mock(spec=TGFSDirectory)
        mock_listing = [Mock(spec=TGFSDirectory), Mock(spec=TGFSFileRef)]
        
        mock_root_directory.find_dir.return_value = mock_subdir
        ops_instance._client.dir_api.ls.return_value = mock_listing
        
        result = ops_instance.ls("/subdir")
        
        mock_root_directory.find_dir.assert_called_once_with("subdir")
        ops_instance._client.dir_api.ls.assert_called_once_with(mock_subdir)
        assert result == mock_listing

    def test_ls_file(self, ops_instance, mock_root_directory):
        mock_file_ref = Mock(spec=TGFSFileRef)
        
        # When find_dir fails, it should try to get file
        mock_root_directory.find_dir.side_effect = FileOrDirectoryDoesNotExist("not found")
        ops_instance._client.dir_api.get_fr.return_value = mock_file_ref
        
        result = ops_instance.ls("/file.txt")
        
        mock_root_directory.find_dir.assert_called_once_with("file.txt")
        ops_instance._client.dir_api.get_fr.assert_called_once_with(mock_root_directory, "file.txt")
        assert result == mock_file_ref

    def test_ls_root_directory(self, ops_instance, mock_root_directory):
        mock_listing = [Mock(spec=TGFSDirectory)]
        ops_instance._client.dir_api.ls.return_value = mock_listing
        
        result = ops_instance.ls("/")
        
        ops_instance._client.dir_api.ls.assert_called_once_with(mock_root_directory)
        assert result == mock_listing

    @pytest.mark.asyncio
    async def test_desc_success(self, ops_instance, mock_root_directory):
        mock_file_ref = Mock(spec=TGFSFileRef)
        mock_file_desc = Mock(spec=TGFSFileDesc)
        
        # Mock ls to return a file reference
        mock_root_directory.find_dir.side_effect = FileOrDirectoryDoesNotExist("not found")
        ops_instance._client.dir_api.get_fr.return_value = mock_file_ref
        ops_instance._client.file_api.desc = AsyncMock(return_value=mock_file_desc)
        
        result = await ops_instance.desc("/file.txt")
        
        ops_instance._client.file_api.desc.assert_called_once_with(mock_file_ref)
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_desc_directory_raises_error(self, ops_instance, mock_root_directory):
        # Mock ls to return a directory (list) instead of file reference
        mock_listing = [Mock(spec=TGFSDirectory)]
        mock_root_directory.find_dir.return_value = Mock(spec=TGFSDirectory)
        ops_instance._client.dir_api.ls.return_value = mock_listing
        
        with pytest.raises(FileOrDirectoryDoesNotExist):
            await ops_instance.desc("/directory")

    @pytest.mark.asyncio
    async def test_cp_dir(self, ops_instance, mock_root_directory):
        mock_source_dir = Mock(spec=TGFSDirectory)
        mock_dest_dir = Mock(spec=TGFSDirectory)
        mock_copied_dir = Mock(spec=TGFSDirectory)
        
        # Setup source directory finding
        mock_source_parent = Mock(spec=TGFSDirectory)
        mock_root_directory.find_dir.side_effect = lambda name: {
            "source_parent": mock_source_parent,
            "dest_parent": mock_dest_dir
        }.get(name, Mock())
        
        mock_source_parent.find_dir.return_value = mock_source_dir
        
        ops_instance._client.dir_api.create = AsyncMock(return_value=mock_copied_dir)
        
        # Mock cd to return appropriate directories
        with patch.object(ops_instance, 'cd') as mock_cd:
            mock_cd.side_effect = [mock_source_parent, mock_dest_dir]
            
            result = await ops_instance.cp_dir("/source_parent/src_dir", "/dest_parent/dest_dir")
        
        mock_source_parent.find_dir.assert_called_once_with("src_dir")
        ops_instance._client.dir_api.create.assert_called_once_with(
            "dest_dir", mock_dest_dir, mock_source_dir
        )
        assert result == (mock_source_dir, mock_copied_dir)

    @pytest.mark.asyncio
    async def test_cp_file(self, ops_instance):
        mock_source_file = Mock(spec=TGFSFileRef)
        mock_dest_dir = Mock(spec=TGFSDirectory)
        mock_copied_file = Mock(spec=TGFSFileRef)
        
        mock_source_dir = Mock(spec=TGFSDirectory)
        mock_source_dir.find_file.return_value = mock_source_file
        
        ops_instance._client.file_api.copy = AsyncMock(return_value=mock_copied_file)
        
        with patch.object(ops_instance, 'cd') as mock_cd:
            mock_cd.side_effect = [mock_source_dir, mock_dest_dir]
            
            result = await ops_instance.cp_file("/src/file.txt", "/dest/new_file.txt")
        
        mock_source_dir.find_file.assert_called_once_with("file.txt")
        ops_instance._client.file_api.copy.assert_called_once_with(
            mock_dest_dir, mock_source_file, "new_file.txt"
        )
        assert result == (mock_source_file, mock_copied_file)

    @pytest.mark.asyncio
    async def test_cp_file_same_name(self, ops_instance):
        mock_source_file = Mock(spec=TGFSFileRef)
        mock_dest_dir = Mock(spec=TGFSDirectory)
        mock_copied_file = Mock(spec=TGFSFileRef)
        
        mock_source_dir = Mock(spec=TGFSDirectory)
        mock_source_dir.find_file.return_value = mock_source_file
        
        ops_instance._client.file_api.copy = AsyncMock(return_value=mock_copied_file)
        
        with patch.object(ops_instance, 'cd') as mock_cd:
            mock_cd.side_effect = [mock_source_dir, mock_dest_dir]
            
            result = await ops_instance.cp_file("/src/file.txt", "/dest/")
        
        # Should use original filename when no basename in destination  
        ops_instance._client.file_api.copy.assert_called_once_with(
            mock_dest_dir, mock_source_file, "file.txt"
        )

    @pytest.mark.asyncio
    async def test_mkdir_simple(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_new_dir = Mock(spec=TGFSDirectory)
        
        ops_instance._client.dir_api.create = AsyncMock(return_value=mock_new_dir)
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            result = await ops_instance.mkdir("/parent/new_dir", parents=False)
        
        ops_instance._client.dir_api.create.assert_called_once_with("new_dir", mock_parent_dir)
        assert result == mock_new_dir

    @pytest.mark.asyncio
    async def test_mkdir_with_parents(self, ops_instance):
        mock_root_dir = Mock(spec=TGFSDirectory)
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_intermediate_dir = Mock(spec=TGFSDirectory)
        mock_new_dir = Mock(spec=TGFSDirectory)
        
        # Mock the parent directory creation
        mock_root_dir.find_dir.side_effect = FileOrDirectoryDoesNotExist("not found")
        ops_instance._client.dir_api.create = AsyncMock()
        ops_instance._client.dir_api.create.side_effect = [
            mock_intermediate_dir,  # Create intermediate directory
            mock_new_dir  # Create final directory
        ]
        
        with patch.object(ops_instance, 'cd', return_value=mock_root_dir):
            result = await ops_instance.mkdir("/parent/child/new_dir", parents=True)
        
        # Should create both parent and child directories
        assert ops_instance._client.dir_api.create.call_count == 2
        assert result == mock_new_dir

    @pytest.mark.asyncio
    async def test_touch_new_file(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_parent_dir.find_file.side_effect = FileOrDirectoryDoesNotExist("not found")
        
        ops_instance._client.file_api.upload = AsyncMock()
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            await ops_instance.touch("/parent/new_file.txt")
        
        mock_parent_dir.find_file.assert_called_once_with("new_file.txt")
        ops_instance._client.file_api.upload.assert_called_once()
        
        # Check that FileMessageEmpty was used
        call_args = ops_instance._client.file_api.upload.call_args
        assert call_args[0][0] == mock_parent_dir
        # The second argument should be a FileMessageEmpty

    @pytest.mark.asyncio
    async def test_touch_existing_file(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_existing_file = Mock(spec=TGFSFileRef)
        mock_parent_dir.find_file.return_value = mock_existing_file
        
        ops_instance._client.file_api.upload = AsyncMock()
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            await ops_instance.touch("/parent/existing_file.txt")
        
        # Should not call upload if file exists
        ops_instance._client.file_api.upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_mv_dir(self, ops_instance):
        mock_source_dir = Mock(spec=TGFSDirectory)
        mock_dest_dir = Mock(spec=TGFSDirectory)
        
        ops_instance._client.dir_api.rm_dangerously = AsyncMock()
        
        with patch.object(ops_instance, 'cp_dir', return_value=(mock_source_dir, mock_dest_dir)):
            result = await ops_instance.mv_dir("/src/dir", "/dest/dir")
        
        ops_instance._client.dir_api.rm_dangerously.assert_called_once_with(mock_source_dir)
        assert result == mock_dest_dir

    @pytest.mark.asyncio
    async def test_mv_file(self, ops_instance):
        mock_source_file = Mock(spec=TGFSFileRef)
        mock_dest_file = Mock(spec=TGFSFileRef)
        
        ops_instance._client.file_api.rm = AsyncMock()
        
        with patch.object(ops_instance, 'cp_file', return_value=(mock_source_file, mock_dest_file)):
            result = await ops_instance.mv_file("/src/file.txt", "/dest/file.txt")
        
        ops_instance._client.file_api.rm.assert_called_once_with(mock_source_file)
        assert result == mock_dest_file

    @pytest.mark.asyncio
    async def test_rm_dir_recursive(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_dir_to_remove = Mock(spec=TGFSDirectory)
        
        mock_parent_dir.find_dir.return_value = mock_dir_to_remove
        ops_instance._client.dir_api.rm_dangerously = AsyncMock()
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            result = await ops_instance.rm_dir("/parent/dir_to_remove", recursive=True)
        
        mock_parent_dir.find_dir.assert_called_once_with("dir_to_remove")
        ops_instance._client.dir_api.rm_dangerously.assert_called_once_with(mock_dir_to_remove)
        assert result == mock_dir_to_remove

    @pytest.mark.asyncio
    async def test_rm_dir_non_recursive(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_dir_to_remove = Mock(spec=TGFSDirectory)
        
        mock_parent_dir.find_dir.return_value = mock_dir_to_remove
        ops_instance._client.dir_api.rm_empty = AsyncMock()
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            result = await ops_instance.rm_dir("/parent/dir_to_remove", recursive=False)
        
        ops_instance._client.dir_api.rm_empty.assert_called_once_with(mock_dir_to_remove)
        assert result == mock_dir_to_remove

    @pytest.mark.asyncio
    async def test_rm_file(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_file_to_remove = Mock(spec=TGFSFileRef)
        
        mock_parent_dir.find_file.return_value = mock_file_to_remove
        ops_instance._client.file_api.rm = AsyncMock()
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            result = await ops_instance.rm_file("/parent/file_to_remove.txt")
        
        mock_parent_dir.find_file.assert_called_once_with("file_to_remove.txt")
        ops_instance._client.file_api.rm.assert_called_once_with(mock_file_to_remove)
        assert result == mock_file_to_remove

    @pytest.mark.asyncio
    async def test_upload_from_local_success(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_file_desc = Mock(spec=TGFSFileDesc)
        mock_file_message = Mock()
        
        ops_instance._client.file_api.upload = AsyncMock(return_value=mock_file_desc)
        
        with patch.object(os.path, 'exists', return_value=True), \
             patch.object(os.path, 'isfile', return_value=True), \
             patch.object(ops_instance, 'cd', return_value=mock_parent_dir), \
             patch('tgfs.core.ops.FileMessageFromPath') as mock_file_message_class:
            
            mock_file_message_class.new.return_value = mock_file_message
            
            result = await ops_instance.upload_from_local("/local/file.txt", "/remote/file.txt")
        
        mock_file_message_class.new.assert_called_once_with(
            path="/local/file.txt", name="file.txt"
        )
        ops_instance._client.file_api.upload.assert_called_once_with(
            mock_parent_dir, mock_file_message
        )
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_upload_from_local_file_not_exists(self, ops_instance):
        with patch.object(os.path, 'exists', return_value=False):
            with pytest.raises(FileOrDirectoryDoesNotExist):
                await ops_instance.upload_from_local("/nonexistent/file.txt", "/remote/file.txt")

    @pytest.mark.asyncio
    async def test_upload_from_local_not_a_file(self, ops_instance):
        with patch.object(os.path, 'exists', return_value=True), \
             patch.object(os.path, 'isfile', return_value=False):
            with pytest.raises(FileOrDirectoryDoesNotExist):
                await ops_instance.upload_from_local("/local/directory", "/remote/file.txt")

    @pytest.mark.asyncio
    async def test_upload_from_bytes(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_file_desc = Mock(spec=TGFSFileDesc)
        test_data = b"test file content"
        
        ops_instance._client.file_api.upload = AsyncMock(return_value=mock_file_desc)
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            result = await ops_instance.upload_from_bytes(test_data, "/remote/file.txt")
        
        ops_instance._client.file_api.upload.assert_called_once()
        call_args = ops_instance._client.file_api.upload.call_args
        assert call_args[0][0] == mock_parent_dir
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_upload_from_stream(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_file_desc = Mock(spec=TGFSFileDesc)
        
        async def mock_stream():
            yield b"chunk1"
            yield b"chunk2"
        
        ops_instance._client.file_api.upload = AsyncMock(return_value=mock_file_desc)
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            result = await ops_instance.upload_from_stream(mock_stream(), 1024, "/remote/file.txt")
        
        ops_instance._client.file_api.upload.assert_called_once()
        call_args = ops_instance._client.file_api.upload.call_args
        assert call_args[0][0] == mock_parent_dir
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_import_from_existing_file_message(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_file_desc = Mock(spec=TGFSFileDesc)
        
        # Create mock message with document
        mock_document = Mock()
        mock_document.size = 2048
        mock_message = Mock(spec=MessageRespWithDocument)
        mock_message.document = mock_document
        mock_message.message_id = 123456
        
        ops_instance._client.file_api.upload = AsyncMock(return_value=mock_file_desc)
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            result = await ops_instance.import_from_existing_file_message(
                mock_message, "/remote/imported_file.txt"
            )
        
        ops_instance._client.file_api.upload.assert_called_once()
        call_args = ops_instance._client.file_api.upload.call_args
        assert call_args[0][0] == mock_parent_dir
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_download_success(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_file_ref = Mock(spec=TGFSFileRef)
        
        async def mock_data_stream():
            yield b"chunk1"
            yield b"chunk2"
        
        mock_parent_dir.find_file.return_value = mock_file_ref
        ops_instance._client.file_api.retrieve = AsyncMock(return_value=mock_data_stream())
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            result = await ops_instance.download("/remote/file.txt", 0, 1024, "downloaded_file.txt")
        
        mock_parent_dir.find_file.assert_called_once_with("file.txt")
        ops_instance._client.file_api.retrieve.assert_called_once_with(
            mock_file_ref, 0, 1024, "downloaded_file.txt"
        )

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, ops_instance):
        mock_parent_dir = Mock(spec=TGFSDirectory)
        mock_parent_dir.find_file.return_value = None
        
        with patch.object(ops_instance, 'cd', return_value=mock_parent_dir):
            with pytest.raises(FileOrDirectoryDoesNotExist):
                await ops_instance.download("/remote/nonexistent.txt", 0, 1024, "file.txt")

    def test_validate_path_static_method(self):
        # Test the static method directly
        Ops._validate_path("/valid/path")
        
        with pytest.raises(InvalidPath):
            Ops._validate_path("/invalid/")
        
        with pytest.raises(InvalidPath):
            Ops._validate_path("no/leading/slash")