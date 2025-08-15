import os
import tempfile
from typing import AsyncIterator

import pytest
from telethon.tl.types import PeerChannel

from tgfs.core.repository.impl.file_content.file_uploader import (
    FileChunk,
    UploaderFromBuffer,
    UploaderFromPath,
    UploaderFromStream,
    WorkersConfig,
    create_uploader,
)
from tgfs.errors import TaskCancelled, TechnicalError
from tgfs.reqres import (
    FileMessageFromBuffer,
    FileMessageFromPath,
    FileMessageFromStream,
    SaveFilePartResp,
    SendMessageResp,
)
from tgfs.tasks.integrations import TaskTracker
from tgfs.telegram.interface import ITDLibClient, TDLibApi


class TestWorkersConfig:
    def test_default_values(self):
        config = WorkersConfig()
        assert config.small == 3
        assert config.big == 5

    def test_custom_values(self):
        config = WorkersConfig(small=2, big=8)
        assert config.small == 2
        assert config.big == 8


class TestFileChunk:
    def test_creation(self):
        content = b"test data"
        file_part = 5
        chunk = FileChunk(content=content, file_part=file_part)

        assert chunk.content == content
        assert chunk.file_part == file_part


class TestUploaderFromPath:
    @pytest.fixture
    def mock_client(self, mocker):
        client = mocker.AsyncMock(spec=ITDLibClient)
        client.save_file_part = mocker.AsyncMock(
            return_value=SaveFilePartResp(success=True)
        )
        client.save_big_file_part = mocker.AsyncMock(
            return_value=SaveFilePartResp(success=True)
        )
        client.send_small_file = mocker.AsyncMock(
            return_value=SendMessageResp(message_id=123)
        )
        client.send_big_file = mocker.AsyncMock(
            return_value=SendMessageResp(message_id=124)
        )
        return client

    @pytest.fixture
    def test_file(self):
        """Create a temporary test file"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_content = b"Hello, World!" * 100  # 1300 bytes
            f.write(test_content)
            f.flush()
            yield f.name, test_content
        os.unlink(f.name)

    @pytest.fixture
    def mock_task_tracker(self, mocker):
        tracker = mocker.AsyncMock(spec=TaskTracker)
        tracker.cancelled = mocker.AsyncMock(return_value=False)
        tracker.update_progress = mocker.AsyncMock()
        return tracker

    @pytest.mark.asyncio
    async def test_small_file_upload(self, mock_client, test_file, mock_task_tracker):
        file_path, expected_content = test_file
        file_size = len(expected_content)

        file_msg = FileMessageFromPath.new(path=file_path, name="test.txt")
        file_msg.task_tracker = mock_task_tracker

        uploader = UploaderFromPath(
            client=mock_client,
            file_size=file_size,
            on_complete=None,
            task_tracker=mock_task_tracker,
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == file_size
        assert uploader.get_uploaded_file().name == "test.txt"
        mock_client.save_file_part.assert_called()
        mock_task_tracker.update_progress.assert_called()

    @pytest.mark.asyncio
    async def test_big_file_upload(self, mock_client, mock_task_tracker):
        """Test big file upload (>10MB)"""
        big_content = b"x" * (11 * 1024 * 1024)  # 11MB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(big_content)
            f.flush()

            try:
                file_msg = FileMessageFromPath.new(path=f.name, name="big_file.bin")
                file_msg.task_tracker = mock_task_tracker

                uploader = UploaderFromPath(
                    client=mock_client,
                    file_size=len(big_content),
                    on_complete=None,
                    task_tracker=mock_task_tracker,
                )

                uploaded_size = await uploader.upload(file_msg)

                assert uploaded_size == len(big_content)
                mock_client.save_big_file_part.assert_called()
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_upload_with_offset(self, mock_client, test_file):
        file_path, original_content = test_file
        offset = 5
        expected_content = original_content[offset:]

        file_msg = FileMessageFromPath.new(path=file_path, name="test_offset.txt")
        file_msg.offset = offset

        uploader = UploaderFromPath(
            client=mock_client, file_size=len(expected_content), on_complete=None
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == len(expected_content)

    @pytest.mark.asyncio
    async def test_default_file_name(self, mock_client, test_file):
        file_path, _ = test_file

        file_msg = FileMessageFromPath.new(path=file_path)
        file_msg.name = ""  # Clear the name to test default

        uploader = UploaderFromPath(client=mock_client, file_size=100, on_complete=None)

        await uploader.upload(file_msg)

        expected_name = os.path.basename(file_path)
        assert uploader.get_uploaded_file().name == expected_name

    @pytest.mark.asyncio
    async def test_upload_failure_and_retry(self, mock_client, test_file):
        file_path, expected_content = test_file

        # First call fails, second succeeds
        mock_client.save_file_part.side_effect = [
            Exception("Network error"),
            SaveFilePartResp(success=True),
        ]

        file_msg = FileMessageFromPath.new(path=file_path, name="retry_test.txt")

        uploader = UploaderFromPath(
            client=mock_client, file_size=len(expected_content), on_complete=None
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == len(expected_content)
        assert mock_client.save_file_part.call_count >= 1

    @pytest.mark.asyncio
    async def test_task_cancellation(
        self, mock_client, test_file, mock_task_tracker, mocker
    ):
        file_path, expected_content = test_file

        # Simulate cancellation
        mock_task_tracker.cancelled = mocker.AsyncMock(return_value=True)

        file_msg = FileMessageFromPath.new(path=file_path, name="cancelled.txt")
        file_msg.task_tracker = mock_task_tracker

        uploader = UploaderFromPath(
            client=mock_client,
            file_size=len(expected_content),
            on_complete=None,
            task_tracker=mock_task_tracker,
        )

        with pytest.raises(TaskCancelled):
            await uploader.upload(file_msg)

    @pytest.mark.asyncio
    async def test_on_complete_callback(self, mock_client, test_file):
        file_path, expected_content = test_file

        on_complete_called = False

        async def on_complete():
            nonlocal on_complete_called
            on_complete_called = True

        file_msg = FileMessageFromPath.new(path=file_path, name="callback_test.txt")

        uploader = UploaderFromPath(
            client=mock_client, file_size=len(expected_content), on_complete=on_complete
        )

        await uploader.upload(file_msg)

        assert on_complete_called

    @pytest.mark.asyncio
    async def test_send_file(self, mock_client, test_file):
        file_path, expected_content = test_file
        chat_id = PeerChannel(channel_id=123)
        caption = "Test caption"

        file_msg = FileMessageFromPath.new(path=file_path, name="send_test.txt")

        uploader = UploaderFromPath(
            client=mock_client, file_size=len(expected_content), on_complete=None
        )

        await uploader.upload(file_msg)
        response = await uploader.send(chat_id, caption)

        assert isinstance(response, SendMessageResp)
        mock_client.send_small_file.assert_called_once()


class TestUploaderFromBuffer:
    @pytest.fixture
    def mock_client(self, mocker):
        client = mocker.AsyncMock(spec=ITDLibClient)
        client.save_file_part = mocker.AsyncMock(
            return_value=SaveFilePartResp(success=True)
        )
        client.save_big_file_part = mocker.AsyncMock(
            return_value=SaveFilePartResp(success=True)
        )
        return client

    @pytest.mark.asyncio
    async def test_buffer_upload(self, mock_client):
        test_data = b"Buffer test data" * 50  # 800 bytes

        file_msg = FileMessageFromBuffer.new(buffer=test_data, name="buffer_test.txt")

        uploader = UploaderFromBuffer(
            client=mock_client, file_size=len(test_data), on_complete=None
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == len(test_data)
        assert uploader.get_uploaded_file().name == "buffer_test.txt"
        mock_client.save_file_part.assert_called()

    @pytest.mark.asyncio
    async def test_buffer_with_offset(self, mock_client):
        test_data = b"0123456789" * 10  # 100 bytes
        offset = 10
        expected_data = test_data[offset:]

        file_msg = FileMessageFromBuffer.new(buffer=test_data, name="offset_buffer.txt")
        file_msg.offset = offset

        uploader = UploaderFromBuffer(
            client=mock_client, file_size=len(expected_data), on_complete=None
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == len(expected_data)

    @pytest.mark.asyncio
    async def test_default_buffer_name(self, mock_client):
        test_data = b"unnamed buffer data"

        file_msg = FileMessageFromBuffer.new(buffer=test_data)

        uploader = UploaderFromBuffer(
            client=mock_client, file_size=len(test_data), on_complete=None
        )

        await uploader.upload(file_msg)

        assert uploader.get_uploaded_file().name == "unnamed"


class TestUploaderFromStream:
    @pytest.fixture
    def mock_client(self, mocker):
        client = mocker.AsyncMock(spec=ITDLibClient)
        client.save_file_part = mocker.AsyncMock(
            return_value=SaveFilePartResp(success=True)
        )
        return client

    @staticmethod
    async def create_test_stream(chunks: list[bytes]) -> AsyncIterator[bytes]:
        """Create a test async stream from chunks"""
        for chunk in chunks:
            yield chunk

    @pytest.mark.asyncio
    async def test_stream_upload(self, mock_client):
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        total_size = sum(len(chunk) for chunk in chunks)

        stream = self.create_test_stream(chunks)
        file_msg = FileMessageFromStream.new(
            stream=stream, size=total_size, name="stream_test.txt"
        )

        uploader = UploaderFromStream(
            client=mock_client, file_size=total_size, on_complete=None
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == total_size
        assert uploader.get_uploaded_file().name == "stream_test.txt"
        mock_client.save_file_part.assert_called()

    @pytest.mark.asyncio
    async def test_stream_default_name(self, mock_client):
        chunks = [b"data"]
        total_size = sum(len(chunk) for chunk in chunks)

        stream = self.create_test_stream(chunks)
        file_msg = FileMessageFromStream.new(stream=stream, size=total_size)

        uploader = UploaderFromStream(
            client=mock_client, file_size=total_size, on_complete=None
        )

        await uploader.upload(file_msg)

        assert uploader.get_uploaded_file().name == "unnamed"

    @pytest.mark.asyncio
    async def test_stream_chunked_reading(self, mock_client):
        """Test that stream reading handles chunks correctly"""
        # Create chunks that don't align with read boundaries
        chunks = [b"abc", b"defghij", b"klm"]
        total_size = sum(len(chunk) for chunk in chunks)

        stream = self.create_test_stream(chunks)
        file_msg = FileMessageFromStream.new(
            stream=stream, size=total_size, name="chunked.txt"
        )

        uploader = UploaderFromStream(
            client=mock_client, file_size=total_size, on_complete=None
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == total_size


class TestCreateUploaderFactory:
    @pytest.fixture
    def mock_tdlib(self, mocker):
        tdlib = mocker.Mock(spec=TDLibApi)
        tdlib.next_bot = mocker.AsyncMock(spec=ITDLibClient)
        return tdlib

    def test_create_path_uploader(self, mock_tdlib):
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()

            file_msg = FileMessageFromPath.new(
                path=temp_file.name, name="path_test.txt"
            )

            uploader = create_uploader(mock_tdlib, file_msg)

            assert isinstance(uploader, UploaderFromPath)

    def test_create_buffer_uploader(self, mock_tdlib):
        file_msg = FileMessageFromBuffer.new(buffer=b"test", name="buffer_test.txt")

        uploader = create_uploader(mock_tdlib, file_msg)

        assert isinstance(uploader, UploaderFromBuffer)

    def test_create_stream_uploader(self, mock_tdlib):
        async def dummy_stream():
            yield b"data"

        file_msg = FileMessageFromStream.new(
            stream=dummy_stream(), size=4, name="stream_test.txt"
        )

        uploader = create_uploader(mock_tdlib, file_msg)

        assert isinstance(uploader, UploaderFromStream)

    def test_create_uploader_with_callback(self, mock_tdlib):
        async def on_complete():
            pass

        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()

            file_msg = FileMessageFromPath.new(path=temp_file.name)

            uploader = create_uploader(mock_tdlib, file_msg, on_complete=on_complete)

            assert isinstance(uploader, UploaderFromPath)

    def test_create_uploader_invalid_type(self, mock_tdlib, mocker):
        invalid_msg = mocker.Mock()  # Not one of the expected types

        with pytest.raises(TechnicalError, match="Unsupported file message type"):
            create_uploader(mock_tdlib, invalid_msg)


class TestErrorHandling:
    @pytest.fixture
    def mock_client(self, mocker):
        client = mocker.AsyncMock(spec=ITDLibClient)
        return client

    @pytest.mark.asyncio
    async def test_upload_response_failure(self, mock_client, mocker):
        """Test handling of failed upload response"""
        # Mock to fail 5 times, then succeed
        failure_count = 0

        def side_effect(*args, **kwargs):
            nonlocal failure_count
            if failure_count < 5:
                failure_count += 1
                return SaveFilePartResp(success=False)
            return SaveFilePartResp(success=True)

        mock_client.save_file_part = mocker.AsyncMock(side_effect=side_effect)

        test_data = b"test data"
        file_msg = FileMessageFromBuffer.new(buffer=test_data, name="fail_test.txt")

        uploader = UploaderFromBuffer(
            client=mock_client, file_size=len(test_data), on_complete=None
        )

        # Should eventually succeed after retries
        uploaded_size = await uploader.upload(file_msg)
        assert uploaded_size == len(test_data)


class TestConcurrencyAndWorkers:
    @pytest.fixture
    def mock_client(self, mocker):
        client = mocker.AsyncMock(spec=ITDLibClient)
        client.save_file_part = mocker.AsyncMock(
            return_value=SaveFilePartResp(success=True)
        )
        return client

    @pytest.mark.asyncio
    async def test_custom_workers_config(self, mock_client):
        """Test upload with custom worker configuration"""
        test_data = b"concurrent test data" * 10
        workers_config = WorkersConfig(small=2, big=4)

        file_msg = FileMessageFromBuffer.new(buffer=test_data, name="concurrent.txt")

        uploader = UploaderFromBuffer(
            client=mock_client,
            file_size=len(test_data),
            on_complete=None,
            workers=workers_config,
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == len(test_data)

    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, mock_client):
        """Test that multiple parts can be uploaded concurrently"""
        # Use a larger file to ensure multiple parts
        test_data = b"x" * (1024 * 512)  # 512KB

        file_msg = FileMessageFromBuffer.new(buffer=test_data, name="large.txt")

        uploader = UploaderFromBuffer(
            client=mock_client, file_size=len(test_data), on_complete=None
        )

        uploaded_size = await uploader.upload(file_msg)

        assert uploaded_size == len(test_data)
        # Should have made multiple calls due to chunking
        assert mock_client.save_file_part.call_count > 1
