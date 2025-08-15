import json
import pytest

from tgfs.core.api import MessageApi
from tgfs.core.model import TGFSDirectory, TGFSFileVersion, TGFSMetadata
from tgfs.core.repository.impl.metadata.pinned_message import TGMsgMetadataRepository
from tgfs.core.repository.interface import IFileContentRepository
from tgfs.errors import MetadataNotInitialized, NoPinnedMessage
from tgfs.reqres import (
    FileMessageFromBuffer,
    MessageRespWithDocument,
    SentFileMessage,
    Document,
)


class TestTGMsgMetadataRepository:
    @pytest.fixture
    def mock_message_api(self, mocker):
        return mocker.AsyncMock(spec=MessageApi)

    @pytest.fixture
    def mock_fc_repo(self, mocker):
        return mocker.AsyncMock(spec=IFileContentRepository)

    @pytest.fixture
    def repository(self, mock_message_api, mock_fc_repo) -> TGMsgMetadataRepository:
        return TGMsgMetadataRepository(mock_message_api, mock_fc_repo)

    @pytest.fixture
    def sample_metadata(self) -> TGFSMetadata:
        root_dir = TGFSDirectory.root_dir()
        return TGFSMetadata(root_dir)

    @pytest.fixture
    def sample_pinned_message(self) -> MessageRespWithDocument:
        document = Document(
            size=1024,
            id=456,
            access_hash=789,
            file_reference=b"test_reference",
            mime_type="application/json",
        )
        return MessageRespWithDocument(message_id=123, text="", document=document)

    def test_init(self, mock_message_api, mock_fc_repo):
        repo = TGMsgMetadataRepository(mock_message_api, mock_fc_repo)

        assert repo._message_api == mock_message_api
        assert repo._fc_repo == mock_fc_repo
        assert repo._message_id is None
        assert repo.metadata is None

    def test_metadata_file_name_constant(self):
        assert TGMsgMetadataRepository.METADATA_FILE_NAME == "metadata.json"

    @pytest.mark.asyncio
    async def test_push_without_metadata_raises_error(self, repository):
        with pytest.raises(MetadataNotInitialized):
            await repository.push()

    @pytest.mark.asyncio
    async def test_push_new_metadata_creates_pinned_message(
        self, repository, mock_message_api, mock_fc_repo, sample_metadata
    ):
        repository.metadata = sample_metadata

        mock_fc_repo.save.return_value = [SentFileMessage(message_id=456, size=1024)]

        await repository.push()

        mock_fc_repo.save.assert_called_once()
        call_args = mock_fc_repo.save.call_args[0][0]
        assert isinstance(call_args, FileMessageFromBuffer)
        assert call_args.name == "metadata.json"
        assert json.loads(call_args.buffer.decode()) == sample_metadata.to_dict()

        mock_message_api.pin_message.assert_called_once_with(message_id=456)
        assert repository._message_id == 456

    @pytest.mark.asyncio
    async def test_push_existing_metadata_updates_message(
        self, repository, mock_message_api, mock_fc_repo, sample_metadata
    ):
        repository.metadata = sample_metadata
        repository._message_id = 789

        await repository.push()

        mock_fc_repo.update.assert_called_once_with(
            789, json.dumps(sample_metadata.to_dict()).encode(), "metadata.json"
        )
        mock_message_api.pin_message.assert_not_called()
        mock_fc_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_read_all_single_chunk(self, repository):
        async def mock_async_iter():
            yield b"test data chunk"

        result = await repository._read_all(mock_async_iter())

        assert result == b"test data chunk"

    @pytest.mark.asyncio
    async def test_read_all_multiple_chunks(self, repository):
        async def mock_async_iter():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        result = await repository._read_all(mock_async_iter())

        assert result == b"chunk1chunk2chunk3"

    @pytest.mark.asyncio
    async def test_read_all_empty_iterator(self, repository):
        async def mock_async_iter():
            yield b""

        result = await repository._read_all(mock_async_iter())

        assert result == b""

    @pytest.mark.asyncio
    async def test_new_metadata_creates_and_returns_pinned_message(
        self, repository, mock_message_api, mock_fc_repo, sample_pinned_message
    ):
        mock_fc_repo.save.return_value = [SentFileMessage(message_id=123, size=1024)]
        mock_message_api.get_pinned_message.return_value = sample_pinned_message

        result = await repository.new_metadata()

        assert repository.metadata is not None
        assert isinstance(repository.metadata.dir, TGFSDirectory)
        # After new_metadata() is called, the message_id should be set after the push operation

        mock_fc_repo.save.assert_called_once()
        mock_message_api.pin_message.assert_called_once_with(message_id=123)
        mock_message_api.get_pinned_message.assert_called_once()

        assert result == sample_pinned_message

    @pytest.mark.asyncio
    async def test_get_with_existing_pinned_message(
        self,
        repository,
        mock_message_api,
        mock_fc_repo,
        sample_pinned_message,
        sample_metadata,
    ):
        mock_message_api.get_pinned_message.return_value = sample_pinned_message

        async def mock_content_iterator():
            yield json.dumps(sample_metadata.to_dict()).encode()

        mock_fc_repo.get.return_value = mock_content_iterator()

        result = await repository.get()

        mock_message_api.get_pinned_message.assert_called_once()
        mock_fc_repo.get.assert_called_once()

        call_args = mock_fc_repo.get.call_args
        temp_fv = call_args[0][0]
        assert isinstance(temp_fv, TGFSFileVersion)
        assert 123 in temp_fv.message_ids
        assert temp_fv.size == 1024
        assert call_args[1]["begin"] == 0
        assert call_args[1]["end"] == -1
        assert call_args[1]["name"] == "metadata.json"

        assert isinstance(result, TGFSMetadata)
        assert repository._message_id == 123

    @pytest.mark.asyncio
    async def test_get_without_pinned_message_creates_new(
        self, repository, mock_message_api, mock_fc_repo, sample_pinned_message
    ):
        # First call raises NoPinnedMessage, second call returns the message
        mock_message_api.get_pinned_message.side_effect = [
            NoPinnedMessage(),
            sample_pinned_message,
        ]
        mock_fc_repo.save.return_value = [SentFileMessage(message_id=123, size=1024)]

        async def mock_content_iterator():
            # Return minimal metadata for new metadata
            root_dir = TGFSDirectory.root_dir()
            metadata = TGFSMetadata(root_dir)
            yield json.dumps(metadata.to_dict()).encode()

        mock_fc_repo.get.return_value = mock_content_iterator()

        result = await repository.get()

        assert mock_message_api.get_pinned_message.call_count == 2
        mock_fc_repo.save.assert_called_once()
        mock_message_api.pin_message.assert_called_once()
        mock_fc_repo.get.assert_called_once()

        assert isinstance(result, TGFSMetadata)
        assert repository._message_id == 123

    @pytest.mark.asyncio
    async def test_get_handles_complex_metadata_structure(
        self, repository, mock_message_api, mock_fc_repo, sample_pinned_message
    ):
        # Create a more complex metadata structure
        root_dir = TGFSDirectory.root_dir()
        root_dir.create_dir("subdir1", None)
        root_dir.create_dir("subdir2", None)
        complex_metadata = TGFSMetadata(root_dir)

        mock_message_api.get_pinned_message.return_value = sample_pinned_message

        async def mock_content_iterator():
            yield json.dumps(complex_metadata.to_dict()).encode()

        mock_fc_repo.get.return_value = mock_content_iterator()

        result = await repository.get()

        assert isinstance(result, TGFSMetadata)
        assert len(result.dir.children) == 2
        assert "subdir1" in [child.name for child in result.dir.children]
        assert "subdir2" in [child.name for child in result.dir.children]

    @pytest.mark.asyncio
    async def test_push_and_get_integration(
        self,
        repository,
        mock_message_api,
        mock_fc_repo,
        sample_metadata,
        sample_pinned_message,
    ):
        # Test the full cycle: push metadata and then retrieve it
        repository.metadata = sample_metadata

        # Mock save and pin operations
        mock_fc_repo.save.return_value = [SentFileMessage(message_id=999, size=2048)]
        mock_message_api.get_pinned_message.return_value = MessageRespWithDocument(
            message_id=999,
            text="",
            document=Document(
                size=2048,
                id=888,
                access_hash=777,
                file_reference=b"test_ref",
                mime_type="application/json",
            ),
        )

        # Push the metadata
        await repository.push()

        # Mock the content retrieval for get operation
        async def mock_content_iterator():
            yield json.dumps(sample_metadata.to_dict()).encode()

        mock_fc_repo.get.return_value = mock_content_iterator()

        # Clear the in-memory metadata to test retrieval
        repository.metadata = None
        repository._message_id = None

        # Get the metadata back
        retrieved_metadata = await repository.get()

        # Verify the metadata was correctly retrieved
        assert isinstance(retrieved_metadata, TGFSMetadata)
        assert repository._message_id == 999

    @pytest.mark.asyncio
    async def test_multiple_pushes_update_existing_message(
        self, repository, mock_message_api, mock_fc_repo, sample_metadata
    ):
        # Set up initial state
        repository.metadata = sample_metadata
        repository._message_id = 555

        # First push (update)
        await repository.push()
        mock_fc_repo.update.assert_called_once_with(
            555, json.dumps(sample_metadata.to_dict()).encode(), "metadata.json"
        )

        # Reset mock
        mock_fc_repo.reset_mock()

        # Modify metadata and push again
        sample_metadata.dir.create_dir("new_dir", None)
        await repository.push()

        # Should call update again, not save
        mock_fc_repo.update.assert_called_once_with(
            555, json.dumps(sample_metadata.to_dict()).encode(), "metadata.json"
        )
        mock_fc_repo.save.assert_not_called()
        mock_message_api.pin_message.assert_not_called()
