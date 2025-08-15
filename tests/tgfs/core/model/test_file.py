import pytest
import datetime
import json
from unittest.mock import Mock, patch

from tgfs.core.model.file import (
    TGFSFileVersion,
    TGFSFileDesc,
    EMPTY_FILE_MESSAGE,
    INVALID_FILE_SIZE,
    INVALID_VERSION_ID,
)
from tgfs.reqres import SentFileMessage
from tgfs.utils.time import FIRST_DAY_OF_EPOCH, ts
from tgfs.errors import InvalidName


class TestTGFSFileVersion:
    def test_init_with_defaults(self):
        # Test creating a file version with minimal parameters
        version = TGFSFileVersion(id="test-id", updated_at=datetime.datetime.now())

        assert version.id == "test-id"
        assert isinstance(version.updated_at, datetime.datetime)
        assert version._size == INVALID_FILE_SIZE
        assert version.message_ids == []
        assert version.part_sizes == []

    def test_init_with_full_data(self):
        # Test creating a file version with all parameters
        now = datetime.datetime.now()
        version = TGFSFileVersion(
            id="test-id",
            updated_at=now,
            _size=1024,
            message_ids=[123, 456],
            part_sizes=[512, 512],
        )

        assert version.id == "test-id"
        assert version.updated_at == now
        assert version._size == 1024
        assert version.message_ids == [123, 456]
        assert version.part_sizes == [512, 512]

    def test_updated_at_timestamp_property(self):
        # Test that the timestamp property converts datetime correctly
        test_dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        version = TGFSFileVersion(id="test", updated_at=test_dt)

        expected_ts = ts(test_dt)
        assert version.updated_at_timestamp == expected_ts

    def test_size_property_with_valid_size(self):
        # Test size property when _size is already set
        version = TGFSFileVersion(
            id="test", updated_at=datetime.datetime.now(), _size=2048
        )

        assert version.size == 2048

    def test_size_property_calculated_from_parts(self):
        # Test size property when calculated from part sizes
        version = TGFSFileVersion(
            id="test",
            updated_at=datetime.datetime.now(),
            part_sizes=[100, 200, 300],
        )

        assert version.size == 600
        assert version._size == 600  # Should be cached

    def test_size_property_invalid_file_no_parts(self):
        # Test size property with invalid size and no parts
        version = TGFSFileVersion(id="test", updated_at=datetime.datetime.now())

        assert version.size == INVALID_FILE_SIZE

    def test_to_dict(self):
        # Test serialization to dictionary
        test_dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        version = TGFSFileVersion(
            id="test-id",
            updated_at=test_dt,
            message_ids=[123, 456],
            part_sizes=[512, 512],
        )

        result = version.to_dict()
        expected = {
            "type": "FV",
            "id": "test-id",
            "updatedAt": ts(test_dt),
            "messageIds": [123, 456],
            "size": 1024,
        }

        assert result == expected

    @patch("tgfs.core.model.file.uuid")
    @patch("tgfs.core.model.file.datetime")
    def test_empty_factory_method(self, mock_datetime, mock_uuid):
        # Test the empty factory method
        mock_uuid.return_value = "mock-uuid"
        mock_now = datetime.datetime(2023, 1, 1)
        mock_datetime.datetime.now.return_value = mock_now

        version = TGFSFileVersion.empty()

        assert version.id == "mock-uuid"
        assert version.updated_at == mock_now
        assert version.message_ids == []

    @patch("tgfs.core.model.file.uuid")
    @patch("tgfs.core.model.file.datetime")
    def test_from_sent_file_message_single(self, mock_datetime, mock_uuid):
        # Test creating version from a single sent file message
        mock_uuid.return_value = "mock-uuid"
        mock_now = datetime.datetime(2023, 1, 1)
        mock_datetime.datetime.now.return_value = mock_now

        message = SentFileMessage(message_id=123, size=1024)
        version = TGFSFileVersion.from_sent_file_message(message)

        assert version.id == "mock-uuid"
        assert version.updated_at == mock_now
        assert version.message_ids == [123]
        assert version.part_sizes == [1024]

    @patch("tgfs.core.model.file.uuid")
    @patch("tgfs.core.model.file.datetime")
    def test_from_sent_file_message_multiple(self, mock_datetime, mock_uuid):
        # Test creating version from multiple sent file messages
        mock_uuid.return_value = "mock-uuid"
        mock_now = datetime.datetime(2023, 1, 1)
        mock_datetime.datetime.now.return_value = mock_now

        msg1 = SentFileMessage(message_id=123, size=512)
        msg2 = SentFileMessage(message_id=456, size=1024)
        version = TGFSFileVersion.from_sent_file_message(msg1, msg2)

        assert version.id == "mock-uuid"
        assert version.updated_at == mock_now
        assert version.message_ids == [123, 456]
        assert version.part_sizes == [512, 1024]

    def test_from_dict_with_updated_at(self):
        # Test deserialization from dict with valid timestamp
        version = TGFSFileVersion.from_dict(
            {
                "type": "FV",
                "id": "test-id",
                "size": 0,
                "updatedAt": 1672574400000,  # 2023-01-01 12:00:00 in ms
                "messageIds": [123, 456],
            }
        )

        assert version.id == "test-id"
        assert version.updated_at == datetime.datetime.fromtimestamp(1672574400)
        assert version.message_ids == [123, 456]
        assert version.part_sizes == []

    def test_from_dict_no_updated_at(self):
        # Test deserialization from dict without timestamp
        version = TGFSFileVersion.from_dict(
            {
                "type": "FV",
                "id": "test-id",
                "size": 0,
                "messageIds": [123],
            }
        )

        assert version.id == "test-id"
        assert version.updated_at == FIRST_DAY_OF_EPOCH
        assert version.message_ids == [123]

    def test_from_dict_legacy_message_id(self):
        # Test deserialization with legacy messageId field
        version = TGFSFileVersion.from_dict(
            {
                "type": "FV",
                "id": "test-id",
                "messageId": 123,
            }
        )

        assert version.id == "test-id"
        assert version.message_ids == [123]

    def test_from_dict_empty_file_message(self):
        # Test deserialization with empty file message
        version = TGFSFileVersion.from_dict(
            {
                "id": "test-id",
                "messageId": EMPTY_FILE_MESSAGE,
            }
        )

        assert version.id == "test-id"
        assert version.message_ids == []

    def test_set_invalid(self):
        # Test making a version invalid
        version = TGFSFileVersion(
            id="test",
            updated_at=datetime.datetime.now(),
            message_ids=[123, 456],
            part_sizes=[512, 512],
            _size=1024,
        )

        version.set_invalid()

        assert version.message_ids == []
        assert version.part_sizes == []
        assert version._size == INVALID_FILE_SIZE

    def test_is_valid_with_messages(self):
        # Test validity check with message IDs
        version = TGFSFileVersion(
            id="test", updated_at=datetime.datetime.now(), message_ids=[123]
        )

        assert version.is_valid() is True

    def test_is_valid_without_messages(self):
        # Test validity check without message IDs
        version = TGFSFileVersion(id="test", updated_at=datetime.datetime.now())

        assert version.is_valid() is False


class TestTGFSFileDesc:
    def test_init_minimal(self):
        # Test creating file description with minimal parameters
        file_desc = TGFSFileDesc(name="test.txt")

        assert file_desc.name == "test.txt"
        assert file_desc.latest_version_id == ""
        assert isinstance(file_desc.created_at, datetime.datetime)
        assert file_desc.versions == {}

    def test_init_full(self):
        # Test creating file description with all parameters
        created_at = datetime.datetime(2023, 1, 1)
        versions = {"v1": TGFSFileVersion("v1", created_at)}

        file_desc = TGFSFileDesc(
            name="test.txt",
            latest_version_id="v1",
            created_at=created_at,
            versions=versions,
        )

        assert file_desc.name == "test.txt"
        assert file_desc.latest_version_id == "v1"
        assert file_desc.created_at == created_at
        assert file_desc.versions == versions

    def test_post_init_name_validation(self):
        # Test that name validation is called during initialization
        with pytest.raises(InvalidName):
            TGFSFileDesc(name="-invalid")

        with pytest.raises(InvalidName):
            TGFSFileDesc(name="invalid/name")

    def test_updated_at_timestamp_no_versions(self):
        # Test timestamp property with no versions
        created_at = datetime.datetime(2023, 1, 1)
        file_desc = TGFSFileDesc(name="test.txt", created_at=created_at)

        assert file_desc.updated_at_timestamp == ts(created_at)

    def test_updated_at_timestamp_with_versions(self):
        # Test timestamp property with versions
        created_at = datetime.datetime(2023, 1, 1)
        version_dt = datetime.datetime(2023, 1, 2)
        version = TGFSFileVersion("v1", version_dt)

        file_desc = TGFSFileDesc(
            name="test.txt",
            created_at=created_at,
            latest_version_id="v1",
            versions={"v1": version},
        )

        assert file_desc.updated_at_timestamp == ts(version_dt)

    def test_to_dict(self):
        # Test serialization to dictionary
        version1 = TGFSFileVersion("v1", datetime.datetime(2023, 1, 1))
        version2 = TGFSFileVersion("v2", datetime.datetime(2023, 1, 2))

        file_desc = TGFSFileDesc(
            name="test.txt",
            latest_version_id="v2",
            versions={"v1": version1, "v2": version2},
        )

        result = file_desc.to_dict()

        assert result["type"] == "F"
        assert len(result["versions"]) == 2
        # Versions should be sorted by timestamp (newest first)
        assert result["versions"][0]["id"] == "v2"
        assert result["versions"][1]["id"] == "v1"

    def test_from_dict_with_versions(self):
        # Test deserialization from dictionary
        file_desc = TGFSFileDesc.from_dict(
            {
                "versions": [
                    {"id": "v1", "updatedAt": 1672531200000, "messageIds": [123]},
                    {"id": "v2", "updatedAt": 1672617600000, "messageIds": [456]},
                ]
            },
            "test.txt",
        )

        assert file_desc.name == "test.txt"
        assert len(file_desc.versions) == 2
        assert file_desc.latest_version_id == "v2"  # Latest by timestamp
        assert "v1" in file_desc.versions
        assert "v2" in file_desc.versions

    def test_from_dict_empty_versions(self):
        # Test deserialization with no versions
        file_desc = TGFSFileDesc.from_dict({"versions": []}, "test.txt")

        assert file_desc.name == "test.txt"
        assert file_desc.versions == {}
        assert file_desc.latest_version_id == INVALID_VERSION_ID

    def test_to_json(self):
        # Test JSON serialization
        file_desc = TGFSFileDesc(name="test.txt")

        json_str = file_desc.to_json()
        data = json.loads(json_str)

        assert data["type"] == "F"
        assert data["versions"] == []

    def test_empty_factory(self):
        # Test empty factory method
        file_desc = TGFSFileDesc.empty("test.txt")

        assert file_desc.name == "test.txt"
        assert file_desc.latest_version_id == ""
        assert file_desc.versions == {}

    def test_get_latest_version_valid(self):
        # Test getting latest version when it exists
        version = TGFSFileVersion("v1", datetime.datetime.now())
        file_desc = TGFSFileDesc(
            name="test.txt", latest_version_id="v1", versions={"v1": version}
        )

        result = file_desc.get_latest_version()

        assert result == version

    def test_get_latest_version_empty(self):
        # Test getting latest version when none exists
        file_desc = TGFSFileDesc(name="test.txt")

        result = file_desc.get_latest_version()

        assert result.id != ""  # Should be an empty version with a UUID
        assert result.message_ids == []

    def test_get_version(self):
        # Test getting specific version
        version = TGFSFileVersion("v1", datetime.datetime.now())
        file_desc = TGFSFileDesc(name="test.txt", versions={"v1": version})

        result = file_desc.get_version("v1")

        assert result == version

    def test_add_version_first(self):
        # Test adding first version
        file_desc = TGFSFileDesc(name="test.txt")
        version = TGFSFileVersion("v1", datetime.datetime.now())

        file_desc.add_version(version)

        assert file_desc.versions["v1"] == version
        assert file_desc.latest_version_id == "v1"

    def test_add_version_newer(self):
        # Test adding newer version
        old_dt = datetime.datetime(2023, 1, 1)
        new_dt = datetime.datetime(2023, 1, 2)

        file_desc = TGFSFileDesc(name="test.txt", created_at=old_dt)
        old_version = TGFSFileVersion("v1", old_dt)
        new_version = TGFSFileVersion("v2", new_dt)

        file_desc.add_version(old_version)
        file_desc.add_version(new_version)

        assert file_desc.latest_version_id == "v2"
        assert file_desc.created_at == old_dt  # Should not change

    def test_add_version_older(self):
        # Test adding older version
        old_dt = datetime.datetime(2023, 1, 1)
        new_dt = datetime.datetime(2023, 1, 2)
        created_dt = datetime.datetime(2023, 1, 3)

        file_desc = TGFSFileDesc(name="test.txt", created_at=created_dt)
        old_version = TGFSFileVersion("v1", old_dt)
        new_version = TGFSFileVersion("v2", new_dt)

        file_desc.add_version(new_version)
        file_desc.add_version(old_version)

        assert file_desc.latest_version_id == "v2"
        assert file_desc.created_at == old_dt  # Should update to earliest

    def test_add_empty_version(self):
        # Test adding empty version
        file_desc = TGFSFileDesc(name="test.txt")

        file_desc.add_empty_version()

        assert len(file_desc.versions) == 1
        version = list(file_desc.versions.values())[0]
        assert version.message_ids == []

    @patch("tgfs.core.model.file.TGFSFileVersion.from_sent_file_message")
    def test_add_version_from_sent_file_message(self, mock_from_sent):
        # Test adding version from sent file message
        mock_version = Mock()
        mock_version.id = "v1"
        mock_version.updated_at = datetime.datetime(2023, 1, 1)
        mock_from_sent.return_value = mock_version

        file_desc = TGFSFileDesc(name="test.txt")
        msg = SentFileMessage(message_id=123, size=1024)

        result = file_desc.add_version_from_sent_file_message(msg)

        mock_from_sent.assert_called_once_with(msg)
        assert result == mock_version

    def test_update_version(self):
        # Test updating existing version
        file_desc = TGFSFileDesc(name="test.txt")
        old_version = TGFSFileVersion("v1", datetime.datetime.now())
        new_version = TGFSFileVersion("v1", datetime.datetime.now())

        file_desc.add_version(old_version)
        file_desc.update_version("v1", new_version)

        assert file_desc.versions["v1"] == new_version

    def test_get_versions_unsorted(self):
        # Test getting versions without sorting
        version1 = TGFSFileVersion("v1", datetime.datetime(2023, 1, 1))
        version2 = TGFSFileVersion("v2", datetime.datetime(2023, 1, 2))

        file_desc = TGFSFileDesc(
            name="test.txt", versions={"v1": version1, "v2": version2}
        )

        result = file_desc.get_versions(sort=False)

        assert len(result) == 2
        assert version1 in result
        assert version2 in result

    def test_get_versions_sorted(self):
        # Test getting versions with sorting
        version1 = TGFSFileVersion("v1", datetime.datetime(2023, 1, 1))
        version2 = TGFSFileVersion("v2", datetime.datetime(2023, 1, 2))

        file_desc = TGFSFileDesc(
            name="test.txt", versions={"v1": version1, "v2": version2}
        )

        result = file_desc.get_versions(sort=True)

        assert len(result) == 2
        assert result[0] == version2  # Newest first
        assert result[1] == version1

    def test_get_versions_exclude_invalid(self):
        # Test getting versions excluding invalid ones
        valid_version = TGFSFileVersion(
            "v1", datetime.datetime.now(), message_ids=[123]
        )
        invalid_version = TGFSFileVersion("v2", datetime.datetime.now())

        file_desc = TGFSFileDesc(
            name="test.txt", versions={"v1": valid_version, "v2": invalid_version}
        )

        result = file_desc.get_versions(exclude_invalid=True)

        assert len(result) == 1
        assert result[0] == valid_version

    def test_delete_version_exists(self):
        # Test deleting existing version
        version1 = TGFSFileVersion("v1", datetime.datetime(2023, 1, 1))
        version2 = TGFSFileVersion("v2", datetime.datetime(2023, 1, 2))

        file_desc = TGFSFileDesc(
            name="test.txt",
            latest_version_id="v2",
            versions={"v1": version1, "v2": version2},
        )

        file_desc.delete_version("v1")

        assert "v1" not in file_desc.versions
        assert "v2" in file_desc.versions
        assert file_desc.latest_version_id == "v2"

    def test_delete_latest_version(self):
        # Test deleting the latest version
        version1 = TGFSFileVersion("v1", datetime.datetime(2023, 1, 1))
        version2 = TGFSFileVersion("v2", datetime.datetime(2023, 1, 2))

        file_desc = TGFSFileDesc(
            name="test.txt",
            latest_version_id="v2",
            versions={"v1": version1, "v2": version2},
        )

        file_desc.delete_version("v2")

        assert "v2" not in file_desc.versions
        assert "v1" in file_desc.versions
        assert file_desc.latest_version_id == "v1"  # Should update to remaining

    def test_delete_last_version(self):
        # Test deleting the last remaining version
        version = TGFSFileVersion("v1", datetime.datetime.now())

        file_desc = TGFSFileDesc(
            name="test.txt", latest_version_id="v1", versions={"v1": version}
        )

        file_desc.delete_version("v1")

        assert file_desc.versions == {}
        assert file_desc.latest_version_id == ""

    def test_delete_version_not_found(self):
        # Test deleting non-existent version
        file_desc = TGFSFileDesc(name="test.txt")

        with pytest.raises(ValueError, match="Version v1 not found in file test.txt"):
            file_desc.delete_version("v1")
