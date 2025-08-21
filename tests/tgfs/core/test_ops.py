import pytest
import os

from tgfs.core.ops import Ops
from tgfs.core.client import Client
from tgfs.core.model import TGFSDirectory, TGFSFileRef, TGFSFileDesc
from tgfs.errors import FileOrDirectoryDoesNotExist, InvalidPath
from tgfs.reqres import MessageRespWithDocument


class TestOps:
    @pytest.fixture
    def mock_client(self, mocker):
        client = mocker.Mock(spec=Client)
        client.name = "test_client"
        client.dir_api = mocker.Mock()
        client.file_api = mocker.Mock()
        client.message_api = mocker.Mock()
        return client

    @pytest.fixture
    def mock_root_directory(self, mocker):
        root = mocker.Mock(spec=TGFSDirectory)
        root.parent = None
        return root

    @pytest.fixture
    def ops(self, mock_client, mock_root_directory) -> Ops:
        mock_client.dir_api.root = mock_root_directory
        return Ops(mock_client)

    @pytest.fixture
    def mock_create_task(self, mocker):
        mock_task_tracker = mocker.AsyncMock()
        mock_task_tracker.mark_failed = mocker.AsyncMock()
        create_task = mocker.patch("tgfs.core.ops.create_upload_task")
        create_task.return_value = mock_task_tracker
        return create_task

    def test_init(self, mock_client):
        ops = Ops(mock_client)
        assert ops._client == mock_client

    def test_validate_path_valid(self, ops):
        # Valid paths should not raise exceptions
        ops._validate_path("/valid/path")
        ops._validate_path("/file.txt")
        ops._validate_path("/a")

    def test_validate_path_invalid_trailing_slash(self, ops):
        with pytest.raises(InvalidPath):
            ops._validate_path("/invalid/path/")

    def test_validate_path_invalid_no_leading_slash(self, ops):
        with pytest.raises(InvalidPath):
            ops._validate_path("invalid/path")

    def test_cd_root(self, ops, mock_root_directory):
        result = ops.cd("/")
        assert result == mock_root_directory

    def test_cd_single_directory(self, ops, mock_root_directory, mocker):
        mock_subdir = mocker.Mock(spec=TGFSDirectory)
        mock_root_directory.find_dir.return_value = mock_subdir

        result = ops.cd("/subdir")

        mock_root_directory.find_dir.assert_called_once_with("subdir")
        assert result == mock_subdir

    def test_cd_nested_directories(self, ops, mock_root_directory, mocker):
        mock_subdir1 = mocker.Mock(spec=TGFSDirectory)
        mock_subdir2 = mocker.Mock(spec=TGFSDirectory)

        mock_root_directory.find_dir.return_value = mock_subdir1
        mock_subdir1.find_dir.return_value = mock_subdir2

        result = ops.cd("/dir1/dir2")

        mock_root_directory.find_dir.assert_called_with("dir1")
        mock_subdir1.find_dir.assert_called_with("dir2")
        assert result == mock_subdir2

    def test_cd_with_parent_directory(self, ops, mock_root_directory, mocker):
        mock_subdir1 = mocker.Mock(spec=TGFSDirectory)
        mock_subdir2 = mocker.Mock(spec=TGFSDirectory)
        mock_parent = mocker.Mock(spec=TGFSDirectory)

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

        result = ops.cd("/dir1/dir2/..")

        # Should navigate to dir1/dir2 then go back to parent
        assert result == mock_parent

    def test_cd_with_current_directory(self, ops, mock_root_directory, mocker):
        mock_subdir = mocker.Mock(spec=TGFSDirectory)
        mock_root_directory.find_dir.return_value = mock_subdir

        result = ops.cd("/subdir/.")

        mock_root_directory.find_dir.assert_called_once_with("subdir")
        assert result == mock_subdir

    def test_stat_file(self, ops, mock_root_directory, mocker):
        mock_file_ref = mocker.Mock(spec=TGFSFileRef)

        ops._client.dir_api.get_fr.return_value = mock_file_ref

        result = ops.stat_file("/file.txt")

        ops._client.dir_api.get_fr.assert_called_once_with(
            mock_root_directory, "file.txt"
        )
        assert result == mock_file_ref

    @pytest.mark.asyncio
    async def test_desc_success(self, ops, mock_root_directory, mocker):
        mock_file_ref = mocker.Mock(spec=TGFSFileRef)
        mock_file_desc = mocker.Mock(spec=TGFSFileDesc)

        # Mock ls to return a file reference
        mock_root_directory.find_dir.side_effect = FileOrDirectoryDoesNotExist(
            "not found"
        )
        ops._client.dir_api.get_fr.return_value = mock_file_ref
        ops._client.file_api.desc = mocker.AsyncMock(return_value=mock_file_desc)

        result = await ops.desc("/file.txt")

        ops._client.file_api.desc.assert_called_once_with(mock_file_ref)
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_desc_directory_raises_error(self, ops, mock_root_directory, mocker):
        # Mock get_fr to raise exception when trying to get file reference for directory
        ops._client.dir_api.get_fr.side_effect = FileOrDirectoryDoesNotExist(
            "not a file"
        )

        with pytest.raises(FileOrDirectoryDoesNotExist):
            await ops.desc("/directory")

    @pytest.mark.asyncio
    async def test_cp_dir(self, ops, mock_root_directory, mocker):
        mock_source_dir = mocker.Mock(spec=TGFSDirectory)
        mock_dest_dir = mocker.Mock(spec=TGFSDirectory)
        mock_copied_dir = mocker.Mock(spec=TGFSDirectory)

        # Setup source directory finding
        mock_source_parent = mocker.Mock(spec=TGFSDirectory)
        mock_root_directory.find_dir.side_effect = lambda name: {
            "source_parent": mock_source_parent,
            "dest_parent": mock_dest_dir,
        }.get(name, mocker.Mock())

        mock_source_parent.find_dir.return_value = mock_source_dir

        ops._client.dir_api.create = mocker.AsyncMock(return_value=mock_copied_dir)

        # Mock cd to return appropriate directories
        mock_cd = mocker.Mock(side_effect=[mock_source_parent, mock_dest_dir])
        mocker.patch.object(ops, "cd", mock_cd)

        result = await ops.cp_dir("/source_parent/src_dir", "/dest_parent/dest_dir")

        mock_source_parent.find_dir.assert_called_once_with("src_dir")
        ops._client.dir_api.create.assert_called_once_with(
            "dest_dir", mock_dest_dir, mock_source_dir
        )
        assert result == (mock_source_dir, mock_copied_dir)

    @pytest.mark.asyncio
    async def test_cp_file(self, ops, mocker):
        mock_source_file = mocker.Mock(spec=TGFSFileRef)
        mock_dest_dir = mocker.Mock(spec=TGFSDirectory)
        mock_copied_file = mocker.Mock(spec=TGFSFileRef)

        mock_source_dir = mocker.Mock(spec=TGFSDirectory)
        mock_source_dir.find_file.return_value = mock_source_file

        ops._client.file_api.copy = mocker.AsyncMock(return_value=mock_copied_file)

        mock_cd = mocker.Mock(side_effect=[mock_source_dir, mock_dest_dir])
        mocker.patch.object(ops, "cd", mock_cd)

        result = await ops.cp_file("/src/file.txt", "/dest/new_file.txt")

        mock_source_dir.find_file.assert_called_once_with("file.txt")
        ops._client.file_api.copy.assert_called_once_with(
            mock_dest_dir, mock_source_file, "new_file.txt"
        )
        assert result == (mock_source_file, mock_copied_file)

    @pytest.mark.asyncio
    async def test_cp_file_same_name(self, ops, mocker):
        mock_source_file = mocker.Mock(spec=TGFSFileRef)
        mock_dest_dir = mocker.Mock(spec=TGFSDirectory)
        mock_copied_file = mocker.Mock(spec=TGFSFileRef)

        mock_source_dir = mocker.Mock(spec=TGFSDirectory)
        mock_source_dir.find_file.return_value = mock_source_file

        ops._client.file_api.copy = mocker.AsyncMock(return_value=mock_copied_file)

        mock_cd = mocker.Mock(side_effect=[mock_source_dir, mock_dest_dir])
        mocker.patch.object(ops, "cd", mock_cd)

        result = await ops.cp_file("/src/file.txt", "/dest/")

        # Should use original filename when no basename in destination
        ops._client.file_api.copy.assert_called_once_with(
            mock_dest_dir, mock_source_file, "file.txt"
        )

    @pytest.mark.asyncio
    async def test_mkdir_simple(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_new_dir = mocker.Mock(spec=TGFSDirectory)

        ops._client.dir_api.create = mocker.AsyncMock(return_value=mock_new_dir)

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        result = await ops.mkdir("/parent/new_dir", parents=False)

        ops._client.dir_api.create.assert_called_once_with("new_dir", mock_parent_dir)
        assert result == mock_new_dir

    @pytest.mark.asyncio
    async def test_mkdir_with_parents(self, ops, mocker):
        mock_root_dir = mocker.Mock(spec=TGFSDirectory)
        mock_intermediate_dir = mocker.Mock(spec=TGFSDirectory)
        mock_new_dir = mocker.Mock(spec=TGFSDirectory)

        # Mock the parent directory creation
        mock_root_dir.find_dir.side_effect = FileOrDirectoryDoesNotExist("not found")
        ops._client.dir_api.create = mocker.AsyncMock()
        ops._client.dir_api.create.side_effect = [
            mock_intermediate_dir,  # Create intermediate directory
            mock_new_dir,  # Create final directory
        ]

        mocker.patch.object(ops, "cd", return_value=mock_root_dir)
        result = await ops.mkdir("/parent/child/new_dir", parents=True)

        # Should create both parent and child directories
        assert ops._client.dir_api.create.call_count == 2
        assert result == mock_new_dir

    @pytest.mark.asyncio
    async def test_touch_new_file(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_parent_dir.find_file.side_effect = FileOrDirectoryDoesNotExist("not found")

        ops._client.file_api.upload = mocker.AsyncMock()

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        await ops.touch("/parent/new_file.txt")

        mock_parent_dir.find_file.assert_called_once_with("new_file.txt")
        ops._client.file_api.upload.assert_called_once()

        # Check that FileMessageEmpty was used
        call_args = ops._client.file_api.upload.call_args
        assert call_args[0][0] == mock_parent_dir
        # The second argument should be a FileMessageEmpty

    @pytest.mark.asyncio
    async def test_touch_existing_file(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_existing_file = mocker.Mock(spec=TGFSFileRef)
        mock_parent_dir.find_file.return_value = mock_existing_file

        ops._client.file_api.upload = mocker.AsyncMock()

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        await ops.touch("/parent/existing_file.txt")

        # Should not call upload if file exists
        ops._client.file_api.upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_mv_dir(self, ops, mocker):
        mock_source_dir = mocker.Mock(spec=TGFSDirectory)
        mock_dest_dir = mocker.Mock(spec=TGFSDirectory)

        ops._client.dir_api.rm_dangerously = mocker.AsyncMock()

        mocker.patch.object(
            ops, "cp_dir", return_value=(mock_source_dir, mock_dest_dir)
        )
        result = await ops.mv_dir("/src/dir", "/dest/dir")

        ops._client.dir_api.rm_dangerously.assert_called_once_with(mock_source_dir)
        assert result == mock_dest_dir

    @pytest.mark.asyncio
    async def test_mv_file(self, ops, mocker):
        mock_source_file = mocker.Mock(spec=TGFSFileRef)
        mock_dest_file = mocker.Mock(spec=TGFSFileRef)

        ops._client.file_api.rm = mocker.AsyncMock()

        mocker.patch.object(
            ops, "cp_file", return_value=(mock_source_file, mock_dest_file)
        )
        result = await ops.mv_file("/src/file.txt", "/dest/file.txt")

        ops._client.file_api.rm.assert_called_once_with(mock_source_file)
        assert result == mock_dest_file

    @pytest.mark.asyncio
    async def test_rm_dir_recursive(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_dir_to_remove = mocker.Mock(spec=TGFSDirectory)

        mock_parent_dir.find_dir.return_value = mock_dir_to_remove
        ops._client.dir_api.rm_dangerously = mocker.AsyncMock()

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        result = await ops.rm_dir("/parent/dir_to_remove", recursive=True)

        mock_parent_dir.find_dir.assert_called_once_with("dir_to_remove")
        ops._client.dir_api.rm_dangerously.assert_called_once_with(mock_dir_to_remove)
        assert result == mock_dir_to_remove

    @pytest.mark.asyncio
    async def test_rm_dir_non_recursive(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_dir_to_remove = mocker.Mock(spec=TGFSDirectory)

        mock_parent_dir.find_dir.return_value = mock_dir_to_remove
        ops._client.dir_api.rm_empty = mocker.AsyncMock()

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        result = await ops.rm_dir("/parent/dir_to_remove", recursive=False)

        ops._client.dir_api.rm_empty.assert_called_once_with(mock_dir_to_remove)
        assert result == mock_dir_to_remove

    @pytest.mark.asyncio
    async def test_rm_file(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_file_to_remove = mocker.Mock(spec=TGFSFileRef)

        mock_parent_dir.find_file.return_value = mock_file_to_remove
        ops._client.file_api.rm = mocker.AsyncMock()

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        result = await ops.rm_file("/parent/file_to_remove.txt")

        mock_parent_dir.find_file.assert_called_once_with("file_to_remove.txt")
        ops._client.file_api.rm.assert_called_once_with(mock_file_to_remove)
        assert result == mock_file_to_remove

    @pytest.mark.asyncio
    async def test_upload_success(self, mock_create_task, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_file_desc = mocker.Mock(spec=TGFSFileDesc)
        mock_file_message = mocker.Mock()
        mock_file_message.name = "test.txt"
        mock_file_message.get_size.return_value = 512

        # Mock task tracker
        task_tracker = mock_create_task.return_value
        task_tracker.mark_completed = mocker.AsyncMock()

        ops._client.file_api.upload = mocker.AsyncMock(return_value=mock_file_desc)
        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)

        result = await ops._upload("/remote", mock_file_message)

        # Assert task was created with correct path and size
        mock_create_task.assert_called_once_with("/test_client/remote/test.txt", 512)

        # Assert task tracker was set on file message
        assert mock_file_message.task_tracker == task_tracker

        # Assert upload was called
        ops._client.file_api.upload.assert_called_once_with(
            mock_parent_dir, mock_file_message
        )

        # Assert task was marked as completed
        task_tracker.mark_completed.assert_called_once()

        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_upload_failure(self, mock_create_task, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_file_message = mocker.Mock()
        mock_file_message.name = "test.txt"
        mock_file_message.get_size.return_value = 512
        upload_error = Exception("Upload failed")

        # Mock task tracker
        task_tracker = mock_create_task.return_value
        task_tracker.mark_failed = mocker.AsyncMock()

        ops._client.file_api.upload = mocker.AsyncMock(side_effect=upload_error)
        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)

        with pytest.raises(Exception, match="Upload failed"):
            await ops._upload("/remote", mock_file_message)

        # Assert task was created
        mock_create_task.assert_called_once_with("/test_client/remote/test.txt", 512)

        # Assert task tracker was set on file message
        assert mock_file_message.task_tracker == task_tracker

        # Assert upload was attempted
        ops._client.file_api.upload.assert_called_once_with(
            mock_parent_dir, mock_file_message
        )

        # Assert task was marked as failed with error message
        task_tracker.mark_failed.assert_called_once_with(str(upload_error))

    @pytest.mark.asyncio
    async def test_upload_from_local_success(self, ops, mocker):
        mock_file_desc = mocker.Mock(spec=TGFSFileDesc)

        mocker.patch.object(os.path, "exists", return_value=True)
        mocker.patch.object(os.path, "isfile", return_value=True)
        mocker.patch.object(os.path, "getsize", return_value=1024)  # Mock file size
        
        # Mock the file opening
        mock_file = mocker.mock_open()
        mocker.patch("builtins.open", mock_file)

        # Mock the _upload method
        mock_upload = mocker.patch.object(ops, "_upload", return_value=mock_file_desc)

        result = await ops.upload_from_local("/local/file.txt", "/remote/file.txt")

        # Should call _upload with correct dirname and FileMessageFromPath
        mock_upload.assert_called_once()
        dirname, file_msg = mock_upload.call_args[0]
        assert dirname == "/remote"
        assert file_msg.name == "file.txt"
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_upload_from_local_file_not_exists(self, ops, mocker):
        mocker.patch.object(os.path, "exists", return_value=False)
        with pytest.raises(FileOrDirectoryDoesNotExist):
            await ops.upload_from_local("/nonexistent/file.txt", "/remote/file.txt")

    @pytest.mark.asyncio
    async def test_upload_from_local_not_a_file(self, ops, mocker):
        mocker.patch.object(os.path, "exists", return_value=True)
        mocker.patch.object(os.path, "isfile", return_value=False)
        with pytest.raises(FileOrDirectoryDoesNotExist):
            await ops.upload_from_local("/local/directory", "/remote/file.txt")

    @pytest.mark.asyncio
    async def test_upload_from_bytes(self, ops, mocker):
        test_data = b"test file content"
        mock_file_desc = mocker.Mock(spec=TGFSFileDesc)

        # Mock the _upload method
        mock_upload = mocker.patch.object(ops, "_upload", return_value=mock_file_desc)

        result = await ops.upload_from_bytes(test_data, "/remote/file.txt")

        # Should call _upload with correct dirname and FileMessageFromBuffer
        mock_upload.assert_called_once()
        dirname, file_msg = mock_upload.call_args[0]
        assert dirname == "/remote"
        assert file_msg.name == "file.txt"
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_upload_from_stream(self, ops, mocker):
        test_size = 1024
        mock_file_desc = mocker.Mock(spec=TGFSFileDesc)

        async def mock_stream():
            yield b"chunk1"
            yield b"chunk2"

        # Mock the _upload method
        mock_upload = mocker.patch.object(ops, "_upload", return_value=mock_file_desc)

        result = await ops.upload_from_stream(
            mock_stream(), test_size, "/remote/file.txt"
        )

        # Should call _upload with correct dirname and FileMessageFromStream
        mock_upload.assert_called_once()
        dirname, file_msg = mock_upload.call_args[0]
        assert dirname == "/remote"
        assert file_msg.name == "file.txt"
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_import_from_existing_file_message(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_file_desc = mocker.Mock(spec=TGFSFileDesc)

        # Create mock message with document
        mock_document = mocker.Mock()
        mock_document.size = 2048
        mock_message = mocker.Mock(spec=MessageRespWithDocument)
        mock_message.document = mock_document
        mock_message.message_id = 123456

        ops._client.file_api.upload = mocker.AsyncMock(return_value=mock_file_desc)

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        result = await ops.import_from_existing_file_message(
            mock_message, "/remote/imported_file.txt"
        )

        ops._client.file_api.upload.assert_called_once()
        call_args = ops._client.file_api.upload.call_args
        assert call_args[0][0] == mock_parent_dir
        assert result == mock_file_desc

    @pytest.mark.asyncio
    async def test_download_success(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_file_ref = mocker.Mock(spec=TGFSFileRef)

        async def mock_data_stream():
            yield b"chunk1"
            yield b"chunk2"

        mock_parent_dir.find_file.return_value = mock_file_ref
        ops._client.file_api.retrieve = mocker.AsyncMock(
            return_value=mock_data_stream()
        )

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        result = await ops.download("/remote/file.txt", 0, 1024, "downloaded_file.txt")

        mock_parent_dir.find_file.assert_called_once_with("file.txt")
        ops._client.file_api.retrieve.assert_called_once_with(
            mock_file_ref, 0, 1024, "downloaded_file.txt"
        )

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, ops, mocker):
        mock_parent_dir = mocker.Mock(spec=TGFSDirectory)
        mock_parent_dir.find_file.return_value = None

        mocker.patch.object(ops, "cd", return_value=mock_parent_dir)
        with pytest.raises(FileOrDirectoryDoesNotExist):
            await ops.download("/remote/nonexistent.txt", 0, 1024, "file.txt")

    def test_validate_path_static_method(self):
        # Test the static method directly
        Ops._validate_path("/valid/path")

        with pytest.raises(InvalidPath):
            Ops._validate_path("/invalid/")

        with pytest.raises(InvalidPath):
            Ops._validate_path("no/leading/slash")
