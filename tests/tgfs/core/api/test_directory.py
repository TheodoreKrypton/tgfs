import datetime

import pytest

from tgfs.core.api.directory import DirectoryApi
from tgfs.core.api.file import FileApi
from tgfs.core.api.message import MessageApi
from tgfs.core.api.metadata import MetaDataApi
from tgfs.core.model import TGFSDirectory, TGFSFileRef, TGFSFileVersion
from tgfs.errors import DirectoryIsNotEmpty


class TestDirectoryApi:
    @pytest.fixture
    def mock_metadata_api(self, mocker):
        return mocker.AsyncMock(spec=MetaDataApi)

    @pytest.fixture
    def mock_file_api(self, mocker):
        return mocker.AsyncMock(spec=FileApi)

    @pytest.fixture
    def mock_message_api(self, mocker):
        return mocker.AsyncMock(spec=MessageApi)

    @pytest.fixture
    def dir_api(self, mock_metadata_api, mock_file_api, mock_message_api) -> DirectoryApi:
        return DirectoryApi(mock_metadata_api, mock_file_api, mock_message_api)

    @staticmethod
    def _make_version(message_ids):
        return TGFSFileVersion(
            id="v1",
            updated_at=datetime.datetime.now(),
            message_ids=list(message_ids),
        )

    @pytest.mark.asyncio
    async def test_rm_empty_directory_no_messages_to_delete(
        self, dir_api, mock_metadata_api, mock_message_api
    ):
        empty_dir = TGFSDirectory.root_dir()

        await dir_api.rm_empty(empty_dir)

        mock_metadata_api.push.assert_called_once()
        mock_message_api.delete_messages.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_rm_empty_non_empty_raises(self, dir_api):
        d = TGFSDirectory.root_dir()
        d.create_file_ref("a.txt", 1)

        with pytest.raises(DirectoryIsNotEmpty):
            await dir_api.rm_empty(d)

    @pytest.mark.asyncio
    async def test_rm_dangerously_collects_subtree_message_ids(
        self, dir_api, mock_file_api, mock_message_api, mock_metadata_api
    ):
        root = TGFSDirectory.root_dir()
        root.create_file_ref("top.txt", 10)

        sub = root.create_dir("sub", None)
        sub.create_file_ref("inner.txt", 20)

        async def fake_collect(fr: TGFSFileRef):
            # Real impl returns the FD message id plus version content ids.
            if fr.message_id == 10:
                return [10, 100, 101]
            if fr.message_id == 20:
                return [20, 200]
            return []

        mock_file_api.collect_message_ids.side_effect = fake_collect

        await dir_api.rm_dangerously(root)

        mock_metadata_api.push.assert_called_once()
        mock_message_api.delete_messages.assert_called_once()
        deleted = mock_message_api.delete_messages.call_args[0][0]
        assert sorted(deleted) == [10, 20, 100, 101, 200]
