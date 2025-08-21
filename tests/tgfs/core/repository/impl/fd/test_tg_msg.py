import datetime
import json
import pytest
from unittest.mock import Mock, AsyncMock

from tgfs.core.api import MessageApi
from tgfs.core.model import TGFSFileDesc, TGFSFileRef, TGFSFileVersion
from tgfs.core.repository.impl.fd.tg_msg import TGMsgFDRepository
from tgfs.core.repository.interface import FDRepositoryResp
from tgfs.errors import MessageNotFound


# Global fixtures for all test classes
@pytest.fixture
def mock_message_api():
    """Mock MessageApi with common configuration"""
    api = Mock(spec=MessageApi)
    api.send_text = AsyncMock()
    api.edit_message_text = AsyncMock()
    api.get_messages = AsyncMock()
    return api


@pytest.fixture
def repository(mock_message_api):
    """Create repository instance with mocked API"""
    return TGMsgFDRepository(mock_message_api)


@pytest.fixture
def sample_file_desc():
    """Create a sample TGFSFileDesc for testing"""
    fd = TGFSFileDesc(name="test_file.txt")
    fd.latest_version_id = "v1"
    
    # Create a file version
    version = TGFSFileVersion(
        id="v1",
        updated_at=datetime.datetime.now(),
        _size=1000,
        message_ids=[12345, 12346],
        part_sizes=[500, 500]
    )
    fd.versions = {"v1": version}
    return fd


@pytest.fixture
def sample_file_ref():
    """Create a sample TGFSFileRef for testing"""
    return TGFSFileRef(message_id=999, name="test_file.txt", location=Mock())


@pytest.fixture
def mock_message():
    """Create a mock message with document"""
    message = Mock()
    message.message_id = 12345
    message.text = '{"name": "test_file.txt", "versions": {}}'
    message.document = Mock()
    message.document.size = 500
    return message


class TestTGMsgFDRepository:
    """Test the main TGMsgFDRepository class"""

    def test_init(self, mock_message_api):
        """Test repository initialization"""
        repository = TGMsgFDRepository(mock_message_api)
        assert repository._TGMsgFDRepository__message_api == mock_message_api


class TestSaveMethod:
    """Test the save method with different scenarios"""

    @pytest.mark.asyncio
    async def test_save_new_file_descriptor(self, repository, mock_message_api, sample_file_desc):
        """Test saving a new file descriptor (fr=None)"""
        mock_message_api.send_text.return_value = 1001
        
        result = await repository.save(sample_file_desc, fr=None)
        
        # Verify the API call
        mock_message_api.send_text.assert_called_once_with(sample_file_desc.to_json())
        
        # Verify the response
        assert isinstance(result, FDRepositoryResp)
        assert result.message_id == 1001
        assert result.fd == sample_file_desc

    @pytest.mark.asyncio
    async def test_save_update_existing_file_descriptor(self, repository, mock_message_api, sample_file_desc, sample_file_ref):
        """Test updating existing file descriptor"""
        mock_message_api.edit_message_text.return_value = 999
        
        result = await repository.save(sample_file_desc, fr=sample_file_ref)
        
        # Verify the API call
        mock_message_api.edit_message_text.assert_called_once_with(
            message_id=999, message=sample_file_desc.to_json()
        )
        
        # Verify the response
        assert isinstance(result, FDRepositoryResp)
        assert result.message_id == 999
        assert result.fd == sample_file_desc

    @pytest.mark.asyncio
    async def test_save_message_not_found_fallback(self, repository, mock_message_api, sample_file_desc, sample_file_ref):
        """Test fallback to creating new message when update fails with MessageNotFound"""
        # First call (edit) fails, second call (send) succeeds
        mock_message_api.edit_message_text.side_effect = MessageNotFound("Message not found")
        mock_message_api.send_text.return_value = 2002
        
        result = await repository.save(sample_file_desc, fr=sample_file_ref)
        
        # Verify both API calls were made
        mock_message_api.edit_message_text.assert_called_once_with(
            message_id=999, message=sample_file_desc.to_json()
        )
        mock_message_api.send_text.assert_called_once_with(sample_file_desc.to_json())
        
        # Verify the response uses the new message ID
        assert isinstance(result, FDRepositoryResp)
        assert result.message_id == 2002
        assert result.fd == sample_file_desc

    @pytest.mark.asyncio
    async def test_save_preserves_other_exceptions(self, repository, mock_message_api, sample_file_desc, sample_file_ref):
        """Test that non-MessageNotFound exceptions are not caught"""
        mock_message_api.edit_message_text.side_effect = Exception("Some other error")
        
        with pytest.raises(Exception, match="Some other error"):
            await repository.save(sample_file_desc, fr=sample_file_ref)
        
        # send_text should not be called
        mock_message_api.send_text.assert_not_called()


class TestGetMethod:
    """Test the get method for retrieving file descriptors"""

    @pytest.mark.asyncio
    async def test_get_valid_message(self, repository, mock_message_api, sample_file_ref):
        """Test getting file descriptor from valid message"""
        # Create mock message with JSON content
        mock_message = Mock()
        mock_message.text = json.dumps({
            "name": "test_file.txt",
            "versions": [
                {
                    "id": "v1",
                    "updatedAt": int(datetime.datetime(2023, 1, 1).timestamp() * 1000),
                    "messageIds": [12345],
                    "size": 1000
                }
            ]
        })
        
        # Mock messages for validation
        file_message = Mock()
        file_message.message_id = 12345
        file_message.document = Mock()
        file_message.document.size = 1000
        
        mock_message_api.get_messages.side_effect = [
            [mock_message],  # First call for descriptor message
            [file_message]   # Second call for file content validation
        ]
        
        result = await repository.get(sample_file_ref, include_all_versions=False)
        
        # Verify API calls
        mock_message_api.get_messages.assert_any_call([999])  # Get descriptor message
        mock_message_api.get_messages.assert_any_call([12345])  # Validate file content
        
        # Verify result
        assert isinstance(result, TGFSFileDesc)
        assert result.name == "test_file.txt"
        assert len(result.versions) == 1

    @pytest.mark.asyncio
    async def test_get_missing_message(self, repository, mock_message_api, sample_file_ref):
        """Test getting file descriptor when message is missing"""
        mock_message_api.get_messages.return_value = [None]
        
        result = await repository.get(sample_file_ref)
        
        # Verify API call
        mock_message_api.get_messages.assert_called_once_with([999])
        
        # Verify result is empty file descriptor
        assert isinstance(result, TGFSFileDesc)
        assert result.name == "test_file.txt"
        assert len(result.versions) == 0  # Empty file descriptor

    @pytest.mark.asyncio
    async def test_get_with_include_all_versions(self, repository, mock_message_api, sample_file_ref):
        """Test getting file descriptor with include_all_versions=True"""
        # Create mock message with multiple versions
        mock_message = Mock()
        mock_message.text = json.dumps({
            "name": "test_file.txt",
            "versions": [
                {
                    "id": "v1",
                    "updatedAt": int(datetime.datetime(2023, 1, 1).timestamp() * 1000),
                    "messageIds": [11111],
                    "size": 1000
                },
                {
                    "id": "v2",
                    "updatedAt": int(datetime.datetime(2023, 2, 1).timestamp() * 1000),
                    "messageIds": [22222],
                    "size": 2000
                }
            ]
        })
        
        # Mock file messages for validation
        file_message1 = Mock()
        file_message1.message_id = 11111
        file_message1.document = Mock()
        file_message1.document.size = 1000
        
        file_message2 = Mock()
        file_message2.message_id = 22222
        file_message2.document = Mock()
        file_message2.document.size = 2000
        
        mock_message_api.get_messages.side_effect = [
            [mock_message],                # First call for descriptor
            [file_message1, file_message2] # Second call for validation
        ]
        
        result = await repository.get(sample_file_ref, include_all_versions=True)
        
        # Verify result has both versions
        assert isinstance(result, TGFSFileDesc)
        assert result.name == "test_file.txt" 
        assert len(result.versions) == 2
        assert "v1" in result.versions
        assert "v2" in result.versions


class TestValidateFvMethod:
    """Test the _validate_fv method for file version validation"""

    @pytest.mark.asyncio
    async def test_validate_fv_all_valid_messages(self, repository, mock_message_api):
        """Test validation with all valid file messages"""
        # Create file descriptor with multiple versions
        fd = TGFSFileDesc(name="multi_version.txt")
        
        version1 = TGFSFileVersion(id="v1", updated_at=datetime.datetime.now(), _size=1000, message_ids=[111, 112])
        version2 = TGFSFileVersion(id="v2", updated_at=datetime.datetime.now(), _size=2000, message_ids=[221, 222])
        
        fd.versions = {"v1": version1, "v2": version2}
        fd.latest_version_id = "v2"
        
        # Mock file messages
        messages = []
        for msg_id in [111, 112, 221, 222]:
            msg = Mock()
            msg.message_id = msg_id
            msg.document = Mock()
            msg.document.size = 500  # Each part is 500 bytes
            messages.append(msg)
        
        mock_message_api.get_messages.return_value = messages
        
        result = await repository._validate_fv(fd, include_all_versions=True)
        
        # Verify API call
        mock_message_api.get_messages.assert_called_once_with([111, 112, 221, 222])
        
        # Verify all versions are valid
        assert result.name == "multi_version.txt"
        assert len(result.versions) == 2
        assert all(version.is_valid() for version in result.versions.values())
        
        # Verify part sizes were populated
        assert version1.part_sizes == [500, 500]
        assert version2.part_sizes == [500, 500]

    @pytest.mark.asyncio
    async def test_validate_fv_missing_messages(self, repository, mock_message_api):
        """Test validation with missing file messages"""
        fd = TGFSFileDesc(name="invalid_file.txt")
        
        version1 = TGFSFileVersion(id="v1", updated_at=datetime.datetime.now(), _size=1000, message_ids=[333, 334])
        fd.versions = {"v1": version1}
        fd.latest_version_id = "v1"
        
        # Return None for missing messages
        mock_message_api.get_messages.return_value = [None, None]
        
        result = await repository._validate_fv(fd, include_all_versions=False)
        
        # Verify result is empty file descriptor due to invalid version
        assert result.name == "invalid_file.txt"
        assert len(result.versions) == 0  # No valid versions

    @pytest.mark.asyncio
    async def test_validate_fv_missing_document(self, repository, mock_message_api):
        """Test validation when message exists but has no document"""
        fd = TGFSFileDesc(name="no_doc.txt")
        
        version1 = TGFSFileVersion(id="v1", updated_at=datetime.datetime.now(), _size=1000, message_ids=[444])
        fd.versions = {"v1": version1}
        fd.latest_version_id = "v1"
        
        # Message exists but has no document
        message_without_doc = Mock()
        message_without_doc.message_id = 444
        message_without_doc.document = None
        
        mock_message_api.get_messages.return_value = [message_without_doc]
        
        result = await repository._validate_fv(fd, include_all_versions=False)
        
        # Verify version is marked invalid
        assert result.name == "no_doc.txt"
        assert len(result.versions) == 0  # No valid versions

    @pytest.mark.asyncio
    async def test_validate_fv_partial_invalid_versions(self, repository, mock_message_api):
        """Test validation with some valid and some invalid versions"""
        fd = TGFSFileDesc(name="mixed_validity.txt")
        
        # Valid version
        version1 = TGFSFileVersion(id="v1", updated_at=datetime.datetime.now(), _size=1000, message_ids=[555])
        # Invalid version (missing message)
        version2 = TGFSFileVersion(id="v2", updated_at=datetime.datetime.now(), _size=2000, message_ids=[666])
        
        fd.versions = {"v1": version1, "v2": version2}
        fd.latest_version_id = "v2"
        
        # First message exists, second is None
        valid_message = Mock()
        valid_message.message_id = 555
        valid_message.document = Mock()
        valid_message.document.size = 1000
        
        mock_message_api.get_messages.return_value = [valid_message, None]
        
        result = await repository._validate_fv(fd, include_all_versions=True)
        
        # Should return the file descriptor with valid versions only
        assert result.name == "mixed_validity.txt"
        assert result == fd  # Returns original fd since has_valid_version is True
        assert version1.is_valid()
        assert not version2.is_valid()

    @pytest.mark.asyncio
    async def test_validate_fv_early_return_on_valid_version(self, repository, mock_message_api):
        """Test early return when include_all_versions=False and first valid version found"""
        fd = TGFSFileDesc(name="early_return.txt")
        
        version1 = TGFSFileVersion(id="v1", updated_at=datetime.datetime.now(), _size=1000, message_ids=[777])
        version2 = TGFSFileVersion(id="v2", updated_at=datetime.datetime.now(), _size=2000, message_ids=[888])
        
        fd.versions = {"v1": version1, "v2": version2}
        fd.latest_version_id = "v1"
        
        # Only first message is valid
        valid_message = Mock()
        valid_message.message_id = 777
        valid_message.document = Mock()
        valid_message.document.size = 1000
        
        mock_message_api.get_messages.return_value = [valid_message, None]
        
        result = await repository._validate_fv(fd, include_all_versions=False)
        
        # Should return early after finding first valid version
        assert result.name == "early_return.txt"
        assert result == fd

    @pytest.mark.asyncio
    async def test_validate_fv_multi_part_file_with_missing_part(self, repository, mock_message_api):
        """Test validation of multi-part file with missing part"""
        fd = TGFSFileDesc(name="multi_part.txt")
        
        # Version with multiple parts, one missing
        version1 = TGFSFileVersion(
            id="v1", 
            updated_at=datetime.datetime.now(), 
            _size=2000, 
            message_ids=[901, 902, 903]
        )
        fd.versions = {"v1": version1}
        fd.latest_version_id = "v1"
        
        # First and third parts exist, second is missing
        part1 = Mock()
        part1.message_id = 901
        part1.document = Mock()
        part1.document.size = 700
        
        part3 = Mock()
        part3.message_id = 903  
        part3.document = Mock()
        part3.document.size = 700
        
        mock_message_api.get_messages.return_value = [part1, None, part3]
        
        result = await repository._validate_fv(fd, include_all_versions=False)
        
        # Version should be invalid due to missing part
        assert result.name == "multi_part.txt"
        assert len(result.versions) == 0  # No valid versions

    @pytest.mark.asyncio 
    async def test_validate_fv_empty_versions(self, repository, mock_message_api):
        """Test validation with empty versions dict"""
        fd = TGFSFileDesc(name="empty_versions.txt")
        fd.versions = {}
        
        mock_message_api.get_messages.return_value = []
        
        result = await repository._validate_fv(fd, include_all_versions=False)
        
        # get_messages is called but with empty list  
        mock_message_api.get_messages.assert_called_once_with([])
        
        # Should return empty file descriptor since no valid versions found
        assert result.name == "empty_versions.txt"
        assert len(result.versions) == 0


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_save_and_get_workflow(self, repository, mock_message_api, sample_file_desc):
        """Test complete save and get workflow"""
        # Save operation
        mock_message_api.send_text.return_value = 5001
        
        save_result = await repository.save(sample_file_desc, fr=None)
        assert save_result.message_id == 5001
        assert save_result.fd == sample_file_desc
        
        # Get operation
        mock_descriptor_message = Mock()
        mock_descriptor_message.text = sample_file_desc.to_json()
        
        # Mock file content message for validation
        file_message = Mock()
        file_message.message_id = 12345
        file_message.document = Mock()
        file_message.document.size = 500
        
        file_message2 = Mock()
        file_message2.message_id = 12346
        file_message2.document = Mock()
        file_message2.document.size = 500
        
        mock_message_api.get_messages.side_effect = [
            [mock_descriptor_message],           # Get descriptor
            [file_message, file_message2]       # Validate content
        ]
        
        file_ref = TGFSFileRef(message_id=5001, name="test_file.txt", location=Mock())
        get_result = await repository.get(file_ref)
        
        assert isinstance(get_result, TGFSFileDesc)
        assert get_result.name == "test_file.txt"
        
        # Verify validation calls were made
        assert mock_message_api.get_messages.call_count == 2

    @pytest.mark.asyncio
    async def test_update_workflow_with_fallback(self, repository, mock_message_api, sample_file_desc, sample_file_ref):
        """Test update workflow with MessageNotFound fallback"""
        # Update fails, then creates new
        mock_message_api.edit_message_text.side_effect = MessageNotFound("Not found")
        mock_message_api.send_text.return_value = 6001
        
        result = await repository.save(sample_file_desc, fr=sample_file_ref)
        
        # Should fall back to creating new message
        assert result.message_id == 6001
        assert result.fd == sample_file_desc
        
        # Both API methods should be called
        assert mock_message_api.edit_message_text.call_count == 1
        assert mock_message_api.send_text.call_count == 1


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_get_with_malformed_json(self, repository, mock_message_api, sample_file_ref):
        """Test error handling with malformed JSON in message"""
        mock_message = Mock()
        mock_message.text = "invalid json content"
        
        mock_message_api.get_messages.return_value = [mock_message]
        
        with pytest.raises(json.JSONDecodeError):
            await repository.get(sample_file_ref)

    @pytest.mark.asyncio
    async def test_validate_with_api_error(self, repository, mock_message_api):
        """Test validation when API call fails"""
        fd = TGFSFileDesc(name="api_error.txt")
        version1 = TGFSFileVersion(id="v1", updated_at=datetime.datetime.now(), _size=1000, message_ids=[999])
        fd.versions = {"v1": version1}
        
        mock_message_api.get_messages.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await repository._validate_fv(fd, include_all_versions=False)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_save_with_empty_file_descriptor(self, repository, mock_message_api):
        """Test saving empty file descriptor"""
        empty_fd = TGFSFileDesc(name="empty.txt")
        mock_message_api.send_text.return_value = 7001
        
        result = await repository.save(empty_fd, fr=None)
        
        assert result.message_id == 7001
        assert result.fd == empty_fd
        mock_message_api.send_text.assert_called_once_with(empty_fd.to_json())

    @pytest.mark.asyncio
    async def test_validate_fv_with_zero_size_file(self, repository, mock_message_api):
        """Test validation of zero-size file"""
        fd = TGFSFileDesc(name="zero_size.txt")
        version1 = TGFSFileVersion(id="v1", updated_at=datetime.datetime.now(), _size=0, message_ids=[1111])
        fd.versions = {"v1": version1}
        
        # Mock zero-size message
        zero_message = Mock()
        zero_message.message_id = 1111
        zero_message.document = Mock()
        zero_message.document.size = 0
        
        mock_message_api.get_messages.return_value = [zero_message]
        
        result = await repository._validate_fv(fd, include_all_versions=False)
        
        assert result.name == "zero_size.txt"
        assert result == fd
        assert version1.is_valid()
        assert version1.part_sizes == [0]

    @pytest.mark.asyncio
    async def test_get_with_complex_file_structure(self, repository, mock_message_api, sample_file_ref):
        """Test getting file descriptor with complex version structure"""
        complex_descriptor = {
            "name": "complex.txt",
            "versions": [
                {
                    "id": "v1",
                    "updatedAt": int(datetime.datetime(2023, 1, 1).timestamp() * 1000),
                    "messageIds": [1001],
                    "size": 1000
                },
                {
                    "id": "v2",
                    "updatedAt": int(datetime.datetime(2023, 2, 1).timestamp() * 1000),
                    "messageIds": [2001, 2002, 2003],
                    "size": 3000
                },
                {
                    "id": "v3",
                    "updatedAt": int(datetime.datetime(2023, 3, 1).timestamp() * 1000),
                    "messageIds": [3001, 3002],
                    "size": 2000
                }
            ]
        }
        
        mock_message = Mock()
        mock_message.text = json.dumps(complex_descriptor)
        
        # Mock all file content messages  
        file_messages = []
        for msg_id in [1001, 2001, 2002, 2003, 3001, 3002]:
            msg = Mock()
            msg.message_id = msg_id
            msg.document = Mock()
            msg.document.size = 1000
            file_messages.append(msg)
        
        mock_message_api.get_messages.side_effect = [
            [mock_message],   # Descriptor message
            file_messages     # File content messages
        ]
        
        result = await repository.get(sample_file_ref, include_all_versions=True)
        
        # Name comes from the file reference, not from JSON content
        assert result.name == "test_file.txt"
        assert len(result.versions) == 3
        # Latest version is determined by timestamp, v3 has the latest timestamp
        assert result.latest_version_id == "v3"

    @pytest.mark.asyncio 
    async def test_validate_fv_with_large_message_id_list(self, repository, mock_message_api):
        """Test validation with large number of message IDs"""
        fd = TGFSFileDesc(name="large_file.txt")
        
        # Create version with many parts (simulate large file)
        message_ids = list(range(8001, 8101))  # 100 message IDs
        version1 = TGFSFileVersion(
            id="v1", 
            updated_at=datetime.datetime.now(), 
            _size=100000, 
            message_ids=message_ids
        )
        fd.versions = {"v1": version1}
        
        # Mock all messages as valid
        file_messages = []
        for msg_id in message_ids:
            msg = Mock()
            msg.message_id = msg_id
            msg.document = Mock()
            msg.document.size = 1000
            file_messages.append(msg)
        
        mock_message_api.get_messages.return_value = file_messages
        
        result = await repository._validate_fv(fd, include_all_versions=False)
        
        # Verify API called with all message IDs
        mock_message_api.get_messages.assert_called_once_with(message_ids)
        
        assert result == fd
        assert version1.is_valid()
        assert len(version1.part_sizes) == 100
        assert all(size == 1000 for size in version1.part_sizes)