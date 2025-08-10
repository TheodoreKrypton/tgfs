import pytest
from unittest.mock import AsyncMock

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.helpers import TotalList
from telethon import types as tlt
from telethon.errors import SessionPasswordNeededError

from tgfs.telegram.impl.telethon import TelethonAPI, Session, login_as_account, login_as_bots
from tgfs.config import Config, TelegramConfig, BotConfig, AccountConfig
from tgfs.errors import TechnicalError, UnDownloadableMessage
from tgfs.reqres import (
    GetMessagesReq, SendTextReq, EditMessageTextReq, EditMessageMediaReq,
    SearchMessageReq, GetPinnedMessageReq, PinMessageReq, SaveFilePartReq,
    SaveBigFilePartReq, SendFileReq, DownloadFileReq, UploadedFile,
    MessageResp
)


class TestTelethonAPI:
    @pytest.fixture
    def mock_client(self, mocker) -> AsyncMock:
        client = mocker.AsyncMock(spec=TelegramClient)
        client.get_messages = mocker.AsyncMock()
        client.send_message = mocker.AsyncMock()
        client.edit_message = mocker.AsyncMock()
        client.send_file = mocker.AsyncMock()
        client.pin_message = mocker.AsyncMock()
        client.iter_download = mocker.AsyncMock()
        return client

    @pytest.fixture
    def telethon_api(self, mock_client) -> TelethonAPI:
        return TelethonAPI(mock_client)

    @pytest.fixture
    def mock_chat(self, mocker):
        return mocker.Mock()

    @pytest.fixture
    def mock_message(self, mocker):
        message = mocker.Mock(spec=tlt.Message)
        message.id = 12345
        message.message = "Test message content"
        message.media = None
        return message

    @pytest.fixture
    def mock_document_message(self, mocker):
        document = mocker.Mock(spec=tlt.Document)
        document.size = 1024
        document.id = 98765
        document.access_hash = 123456789
        document.file_reference = b'test_file_reference'
        document.mime_type = 'text/plain'

        media = mocker.Mock(spec=tlt.MessageMediaDocument)
        media.document = document

        message = mocker.Mock(spec=tlt.Message)
        message.id = 54321
        message.message = "File message"
        message.media = media
        message.document = document
        return message

    def test_init(self, mock_client):
        api = TelethonAPI(mock_client)
        assert api._client == mock_client

    @pytest.mark.asyncio
    async def test_get_messages_raises_error_on_invalid_response(self, telethon_api, mock_chat):
        # Mock invalid response (not TotalList)
        telethon_api._client.get_messages.return_value = []
        
        req = GetMessagesReq(chat=mock_chat, message_ids=(1, 2, 3))
        
        with pytest.raises(TechnicalError, match="Unexpected response type from get_messages"):
            await telethon_api.get_messages(req)

    @pytest.mark.asyncio
    async def test_get_messages_success_with_cache(self, telethon_api, mock_chat, mock_message, mocker):
        # Mock successful response
        total_list = TotalList([mock_message])
        telethon_api._client.get_messages.return_value = total_list
        
        req = GetMessagesReq(chat=mock_chat, message_ids=(12345,))
        
        mock_cache = mocker.Mock()
        mock_cache.find_nonexistent.return_value = [12345]
        mock_cache.__setitem__ = mocker.Mock()
        mock_cache.gets.return_value = []
        
        mocker.patch('tgfs.telegram.impl.telethon.message_cache_by_id', mock_cache)
        
        result = await telethon_api.get_messages(req)
        
        telethon_api._client.get_messages.assert_called_once_with(
            entity=mock_chat, ids=[12345]
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_messages_with_cached_messages(self, telethon_api, mock_chat, mocker):
        req = GetMessagesReq(chat=mock_chat, message_ids=(12345,))
        
        mock_cache = mocker.Mock()
        mock_cache.find_nonexistent.return_value = []  # All messages cached
        mock_cache.gets.return_value = [MessageResp(message_id=12345, text="cached", document=None)]
        
        mocker.patch('tgfs.telegram.impl.telethon.message_cache_by_id', mock_cache)
        
        result = await telethon_api.get_messages(req)
        
        # Should not fetch from API if all messages are cached
        telethon_api._client.get_messages.assert_not_called()
        assert len(result) == 1

    def test_transform_messages_with_text_only(self, mock_message):
        messages = [mock_message]
        
        result = TelethonAPI._transform_messages(messages)
        
        assert len(result) == 1
        assert result[0] is not None
        assert result[0].message_id == 12345
        assert result[0].text == "Test message content"
        assert result[0].document is None

    def test_transform_messages_with_document(self, mock_document_message):
        messages = [mock_document_message]
        
        result = TelethonAPI._transform_messages(messages)
        
        assert len(result) == 1
        assert result[0] is not None
        assert result[0].message_id == 54321
        assert result[0].text == "File message"
        assert result[0].document is not None
        assert result[0].document.size == 1024
        assert result[0].document.id == 98765
        assert result[0].document.mime_type == 'text/plain'

    def test_transform_messages_with_none_message(self, mocker):
        mock_msg = mocker.Mock(spec=tlt.Message)
        mock_msg.id = 123
        mock_msg.message = "test"
        mock_msg.media = None
        messages = [None, mock_msg]
        
        result = TelethonAPI._transform_messages(messages)
        
        assert len(result) == 2
        assert result[0] is None
        assert result[1] is not None

    def test_transform_messages_with_empty_document(self, mocker):
        empty_doc = mocker.Mock(spec=tlt.DocumentEmpty)
        media = mocker.Mock(spec=tlt.MessageMediaDocument)
        media.document = empty_doc
        
        message = mocker.Mock(spec=tlt.Message)
        message.id = 123
        message.message = "test"
        message.media = media
        
        result = TelethonAPI._transform_messages([message])
        
        assert len(result) == 1
        assert result[0] is not None
        assert result[0].document is None

    @pytest.mark.asyncio
    async def test_send_text(self, telethon_api, mock_chat, mocker):
        mock_sent_message = mocker.Mock()
        mock_sent_message.id = 99999
        telethon_api._client.send_message.return_value = mock_sent_message
        
        req = SendTextReq(chat=mock_chat, text="Hello World")
        
        result = await telethon_api.send_text(req)
        
        telethon_api._client.send_message.assert_called_once_with(
            entity=mock_chat, message="Hello World"
        )
        assert result.message_id == 99999

    @pytest.mark.asyncio
    async def test_edit_message_text(self, telethon_api, mock_chat, mocker):
        mock_edited_message = mocker.Mock()
        mock_edited_message.id = 88888
        telethon_api._client.edit_message.return_value = mock_edited_message
        
        req = EditMessageTextReq(chat=mock_chat, message_id=12345, text="Updated text")
        
        mock_cache = mocker.Mock()
        mock_cache.__setitem__ = mocker.Mock()
        
        mocker.patch('tgfs.telegram.impl.telethon.message_cache_by_id', mock_cache)
        result = await telethon_api.edit_message_text(req)
        
        telethon_api._client.edit_message.assert_called_once_with(
            entity=mock_chat, message=12345, text="Updated text"
        )
        mock_cache.__setitem__.assert_called_once_with(12345, None)
        assert result.message_id == 88888

    @pytest.mark.asyncio
    async def test_edit_message_media(self, telethon_api, mock_chat, mocker):
        mock_edited_message = mocker.Mock()
        mock_edited_message.id = 77777
        telethon_api._client.edit_message.return_value = mock_edited_message
        
        uploaded_file = UploadedFile(id=123, parts=10, name="test.txt")
        req = EditMessageMediaReq(chat=mock_chat, message_id=12345, file=uploaded_file)
        
        mock_cache = mocker.Mock()
        mock_cache.__setitem__ = mocker.Mock()
        
        mocker.patch('tgfs.telegram.impl.telethon.message_cache_by_id', mock_cache)
        result = await telethon_api.edit_message_media(req)
        
        telethon_api._client.edit_message.assert_called_once()
        call_args = telethon_api._client.edit_message.call_args
        assert call_args[1]['entity'] == mock_chat
        assert call_args[1]['message'] == 12345
        assert isinstance(call_args[1]['file'], tlt.InputFile)
        mock_cache.__setitem__.assert_called_once_with(12345, None)
        assert result.message_id == 77777

    @pytest.mark.asyncio
    async def test_search_messages(self, telethon_api, mock_chat, mock_message, mocker):
        total_list = TotalList([mock_message])
        telethon_api._client.get_messages.return_value = total_list
        
        req = SearchMessageReq(chat=mock_chat, search="test query")
        
        mock_cache = mocker.patch('tgfs.telegram.impl.telethon.message_cache_by_search')
        mock_cache.__contains__ = mocker.Mock(return_value=False)
        mock_cache.__setitem__ = mocker.Mock()
        
        result = await telethon_api.search_messages(req)
        
        telethon_api._client.get_messages.assert_called_once_with(
            entity=mock_chat, search="test query"
        )
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_search_messages_with_cache(self, telethon_api, mock_chat, mocker):
        req = SearchMessageReq(chat=mock_chat, search="cached query")
        cached_result = (MessageResp(message_id=1, text="cached", document=None),)
        
        mock_cache = mocker.patch('tgfs.telegram.impl.telethon.message_cache_by_search')
        mock_cache.__contains__ = mocker.Mock(return_value=True)
        mock_cache.__getitem__ = mocker.Mock(return_value=cached_result)
        
        result = await telethon_api.search_messages(req)
        
        telethon_api._client.get_messages.assert_not_called()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_pinned_messages(self, telethon_api, mock_chat, mock_message):
        total_list = TotalList([mock_message])
        telethon_api._client.get_messages.return_value = total_list
        
        req = GetPinnedMessageReq(chat=mock_chat)
        
        result = await telethon_api.get_pinned_messages(req)
        
        telethon_api._client.get_messages.assert_called_once()
        call_args = telethon_api._client.get_messages.call_args
        assert call_args[1]['entity'] == mock_chat
        assert isinstance(call_args[1]['filter'], tlt.InputMessagesFilterPinned)
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_pin_message(self, telethon_api, mock_chat):
        req = PinMessageReq(chat=mock_chat, message_id=12345)
        
        await telethon_api.pin_message(req)
        
        telethon_api._client.pin_message.assert_called_once_with(
            entity=mock_chat, message=12345, notify=False
        )

    @pytest.mark.asyncio
    async def test_save_big_file_part(self, telethon_api):
        req = SaveBigFilePartReq(
            file_id=123, file_part=1, bytes=b"test data", file_total_parts=10
        )
        
        telethon_api._client.return_value = True
        
        result = await telethon_api.save_big_file_part(req)
        
        telethon_api._client.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_save_file_part(self, telethon_api):
        req = SaveFilePartReq(file_id=123, file_part=1, bytes=b"test data")
        
        telethon_api._client.return_value = True
        
        result = await telethon_api.save_file_part(req)
        
        telethon_api._client.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_send_big_file(self, telethon_api, mock_chat, mocker):
        mock_sent_message = mocker.Mock(spec=tlt.Message)
        mock_sent_message.id = 66666
        telethon_api._client.send_file.return_value = mock_sent_message
        
        uploaded_file = UploadedFile(id=123, parts=10, name="big_file.zip")
        req = SendFileReq(chat=mock_chat, file=uploaded_file, name="big_file.zip", caption="Big file")
        
        result = await telethon_api.send_big_file(req)
        
        telethon_api._client.send_file.assert_called_once()
        call_args = telethon_api._client.send_file.call_args
        assert call_args[1]['entity'] == mock_chat
        assert isinstance(call_args[1]['file'], tlt.InputFileBig)
        assert call_args[1]['caption'] == "Big file"
        assert call_args[1]['force_document'] is True
        assert result.message_id == 66666

    @pytest.mark.asyncio
    async def test_send_big_file_invalid_response(self, telethon_api, mock_chat):
        telethon_api._client.send_file.return_value = "invalid response"
        
        uploaded_file = UploadedFile(id=123, parts=10, name="test.txt")
        req = SendFileReq(chat=mock_chat, file=uploaded_file, name="test.txt", caption="Test")
        
        with pytest.raises(TechnicalError, match="Unexpected response type from send_file"):
            await telethon_api.send_big_file(req)

    @pytest.mark.asyncio
    async def test_send_small_file(self, telethon_api, mock_chat, mocker):
        mock_sent_message = mocker.Mock(spec=tlt.Message)
        mock_sent_message.id = 55555
        telethon_api._client.send_file.return_value = mock_sent_message
        
        uploaded_file = UploadedFile(id=123, parts=3, name="small_file.txt")
        req = SendFileReq(chat=mock_chat, file=uploaded_file, name="small_file.txt", caption="Small file")
        
        result = await telethon_api.send_small_file(req)
        
        telethon_api._client.send_file.assert_called_once()
        call_args = telethon_api._client.send_file.call_args
        assert call_args[1]['entity'] == mock_chat
        assert isinstance(call_args[1]['file'], tlt.InputFile)
        assert call_args[1]['caption'] == "Small file"
        assert call_args[1]['force_document'] is True
        assert result.message_id == 55555

    @pytest.mark.asyncio
    async def test_send_small_file_invalid_response(self, telethon_api, mock_chat):
        telethon_api._client.send_file.return_value = None
        
        uploaded_file = UploadedFile(id=123, parts=3, name="test.txt")
        req = SendFileReq(chat=mock_chat, file=uploaded_file, name="test.txt", caption="Test")
        
        with pytest.raises(TechnicalError, match="Unexpected response type from send_file"):
            await telethon_api.send_small_file(req)

    @pytest.mark.asyncio
    async def test_download_file_success(self, telethon_api, mock_chat, mock_document_message):
        total_list = TotalList([mock_document_message])
        telethon_api._client.get_messages.return_value = total_list
        
        async def mock_iter_download(*args, **kwargs):
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"
        
        telethon_api._client.iter_download = mock_iter_download
        
        req = DownloadFileReq(
            chat=mock_chat, message_id=54321, begin=0, end=99, chunk_size=32
        )
        
        result = await telethon_api.download_file(req)
        
        telethon_api._client.get_messages.assert_called_once_with(
            entity=mock_chat, ids=[54321]
        )
        assert result.size == 100  # end - begin + 1
        
        # Test the async iterator
        chunks = []
        async for chunk in result.chunks:
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_download_file_message_without_document(self, telethon_api, mock_chat, mock_message):
        total_list = TotalList([mock_message])  # message without document
        telethon_api._client.get_messages.return_value = total_list
        
        req = DownloadFileReq(
            chat=mock_chat, message_id=12345, begin=0, end=99, chunk_size=32
        )
        
        with pytest.raises(UnDownloadableMessage):
            await telethon_api.download_file(req)

    @pytest.mark.asyncio
    async def test_download_file_invalid_range(self, telethon_api, mock_chat, mock_document_message):
        total_list = TotalList([mock_document_message])
        telethon_api._client.get_messages.return_value = total_list
        
        async def mock_iter_download(*args, **kwargs):
            yield b"chunk1"
        
        telethon_api._client.iter_download = mock_iter_download
        
        req = DownloadFileReq(
            chat=mock_chat, message_id=54321, begin=100, end=50, chunk_size=32
        )
        
        result = await telethon_api.download_file(req)
        
        # The error should be raised when iterating through chunks
        with pytest.raises(TechnicalError, match="Invalid range"):
            async for chunk in result.chunks:
                pass

    @pytest.mark.asyncio
    async def test_download_file_chunk_size_larger_than_remaining(self, telethon_api, mock_chat, mock_document_message):
        total_list = TotalList([mock_document_message])
        telethon_api._client.get_messages.return_value = total_list
        
        async def mock_iter_download(*args, **kwargs):
            yield b"very_long_chunk_that_exceeds_remaining_bytes"
        
        telethon_api._client.iter_download = mock_iter_download
        
        req = DownloadFileReq(
            chat=mock_chat, message_id=54321, begin=0, end=9, chunk_size=32  # Only 10 bytes needed
        )
        
        result = await telethon_api.download_file(req)
        
        chunks = []
        async for chunk in result.chunks:
            chunks.append(chunk)
        
        # Should truncate the chunk to exactly 10 bytes
        assert len(chunks[0]) == 10


class TestSession:
    @pytest.fixture
    def session_file_path(self, tmp_path) -> str:
        return str(tmp_path / "test_session.txt")

    @pytest.fixture
    def session(self, session_file_path: str) -> Session:
        return Session(session_file_path)

    def test_init(self, session_file_path):
        session = Session(session_file_path)
        assert session.session_file == session_file_path

    def test_get_existing_session(self, session, session_file_path, mocker):
        # Create session file with a valid telethon session string
        # Using a mock valid session string format
        with open(session_file_path, 'w') as f:
            f.write("1AgAOMTQ5LjE1NC4xNzUuNTABuwIZRrSMhkWR8W3UD3Zfz1UY-")
        
        mocker.patch('telethon.sessions.StringSession.__init__', return_value=None)
        result = session.get()
        assert result is not None

    def test_get_nonexistent_session(self, session):
        result = session.get()
        assert result is None

    def test_save_multibot_creates_directory(self, tmp_path):
        session_dir = tmp_path / "sessions"
        session_file = session_dir / "bot123.session"
        session = Session(str(session_file))
        
        session.save_multibot("test_session_string")
        
        assert session_dir.exists()
        assert session_file.exists()
        with open(session_file, 'r') as f:
            assert f.read() == "test_session_string"

    def test_save_multibot_existing_file_as_directory_raises_error(self, tmp_path):
        # Create a file where directory should be
        session_dir_path = tmp_path / "session_file"
        session_dir_path.write_text("existing file")
        
        session_file = session_dir_path / "bot123.session"
        session = Session(str(session_file))
        
        with pytest.raises(Exception, match="is a session file which only supports one bot session"):
            session.save_multibot("test_session_string")

    def test_save_creates_directory_if_needed(self, tmp_path):
        session_dir = tmp_path / "new_dir"
        session_file = session_dir / "session.txt"
        session = Session(str(session_file))
        
        session.save("test_session_string")
        
        assert session_dir.exists()
        assert session_file.exists()
        with open(session_file, 'r') as f:
            assert f.read() == "test_session_string"

    def test_save_overwrites_existing_file(self, session, session_file_path):
        # Create existing file
        with open(session_file_path, 'w') as f:
            f.write("old_session")
        
        session.save("new_session_string")
        
        with open(session_file_path, 'r') as f:
            assert f.read() == "new_session_string"


class TestLoginAsAccount:
    @pytest.fixture
    def mock_config(self, mocker):
        config = mocker.Mock(spec=Config)
        config.telegram = mocker.Mock(spec=TelegramConfig)
        config.telegram.account = mocker.Mock(spec=AccountConfig)
        config.telegram.account.session_file = "/path/to/account.session"
        config.telegram.api_id = 12345
        config.telegram.api_hash = "test_api_hash"
        return config

    @pytest.mark.asyncio
    async def test_login_as_account_no_account_config(self, mocker):
        config = mocker.Mock(spec=Config)
        config.telegram = mocker.Mock(spec=TelegramConfig)
        config.telegram.account = None
        
        with pytest.raises(TechnicalError, match="Account configuration is missing"):
            await login_as_account(config)

    @pytest.mark.asyncio
    async def test_login_as_account_with_existing_session(self, mock_config, mocker):
        mock_session_string = mocker.Mock(spec=StringSession)
        mock_client = mocker.Mock(spec=TelegramClient)
        mock_user = mocker.Mock(spec=tlt.User)
        mock_user.username = "testuser"
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        
        mock_session_instance = MockSession.return_value
        mock_session_instance.get.return_value = mock_session_string
        
        MockTelegramClient.return_value = mock_client
        mock_client.connect = mocker.AsyncMock()
        mock_client.get_me = mocker.AsyncMock(return_value=mock_user)
        
        result = await login_as_account(mock_config)
        
        MockTelegramClient.assert_called_once_with(
            mock_session_string, 12345, "test_api_hash"
        )
        mock_client.connect.assert_called_once()
        assert result == mock_client

    @pytest.mark.asyncio
    async def test_login_as_account_new_session_success(self, mock_config, mocker):
        mock_client = mocker.Mock(spec=TelegramClient)
        mock_user = mocker.Mock(spec=tlt.User)
        mock_user.username = "newuser"
        mock_sms_req = mocker.Mock()
        mock_sms_req.phone_code_hash = "test_hash"
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        mock_input = mocker.patch('builtins.input')
        
        mock_session_instance = MockSession.return_value
        mock_session_instance.get.return_value = None
        mock_session_instance.save = mocker.Mock()
        
        MockTelegramClient.return_value = mock_client
        mock_client.connect = mocker.AsyncMock()
        mock_client.send_code_request = mocker.AsyncMock(return_value=mock_sms_req)
        mock_client.sign_in = mocker.AsyncMock()
        mock_client.get_me = mocker.AsyncMock(return_value=mock_user)
        mock_client.session = mocker.Mock()
        mock_client.session.save.return_value = "new_session_string"
        
        mock_input.side_effect = ["+1234567890", "123456"]
        
        result = await login_as_account(mock_config)
        
        mock_client.send_code_request.assert_called_once_with("+1234567890", force_sms=False)
        mock_client.sign_in.assert_called_once_with(
            phone="+1234567890", code="123456", phone_code_hash="test_hash"
        )
        mock_session_instance.save.assert_called_once_with("new_session_string")
        assert result == mock_client

    @pytest.mark.asyncio
    async def test_login_as_account_with_2fa(self, mock_config, mocker):
        mock_client = mocker.Mock(spec=TelegramClient)
        mock_user = mocker.Mock(spec=tlt.User)
        mock_user.username = "user2fa"
        mock_sms_req = mocker.Mock()
        mock_sms_req.phone_code_hash = "test_hash"
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        mock_input = mocker.patch('builtins.input')
        mock_getpass = mocker.patch('tgfs.telegram.impl.telethon.getpass')
        
        mock_session_instance = MockSession.return_value
        mock_session_instance.get.return_value = None
        mock_session_instance.save = mocker.Mock()
        
        MockTelegramClient.return_value = mock_client
        mock_client.connect = mocker.AsyncMock()
        mock_client.send_code_request = mocker.AsyncMock(return_value=mock_sms_req)
        
        # First sign_in raises SessionPasswordNeededError, second succeeds
        mock_client.sign_in = mocker.AsyncMock(side_effect=[SessionPasswordNeededError("Mock request"), None])
        mock_client.get_me = mocker.AsyncMock(return_value=mock_user)
        mock_client.session = mocker.Mock()
        mock_client.session.save.return_value = "new_session_string"
        
        mock_input.side_effect = ["+1234567890", "123456"]
        mock_getpass.return_value = "2fa_password"
        
        result = await login_as_account(mock_config)
        
        assert mock_client.sign_in.call_count == 2
        # First call with phone and code
        first_call = mock_client.sign_in.call_args_list[0]
        assert first_call[1]['phone'] == "+1234567890"
        assert first_call[1]['code'] == "123456"
        # Second call with 2FA password
        second_call = mock_client.sign_in.call_args_list[1]
        assert second_call[1]['password'] == "2fa_password"
        assert result == mock_client

    @pytest.mark.asyncio
    async def test_login_as_account_sign_in_error(self, mock_config, mocker):
        mock_client = mocker.Mock(spec=TelegramClient)
        mock_sms_req = mocker.Mock()
        mock_sms_req.phone_code_hash = "test_hash"
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        mock_input = mocker.patch('builtins.input')
        
        mock_session_instance = MockSession.return_value
        mock_session_instance.get.return_value = None
        
        MockTelegramClient.return_value = mock_client
        mock_client.connect = mocker.AsyncMock()
        mock_client.send_code_request = mocker.AsyncMock(return_value=mock_sms_req)
        mock_client.sign_in = mocker.AsyncMock(side_effect=Exception("Sign in failed"))
        
        mock_input.side_effect = ["+1234567890", "123456"]
        
        with pytest.raises(Exception, match="Sign in failed"):
            await login_as_account(mock_config)

    @pytest.mark.asyncio
    async def test_login_as_account_no_username(self, mock_config, mocker):
        mock_client = mocker.Mock(spec=TelegramClient)
        mock_user = mocker.Mock(spec=tlt.User)
        mock_user.username = None
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        mock_logger = mocker.patch('tgfs.telegram.impl.telethon.logger')
        
        mock_session_instance = MockSession.return_value
        mock_session_instance.get.return_value = mocker.Mock(spec=StringSession)
        
        MockTelegramClient.return_value = mock_client
        mock_client.connect = mocker.AsyncMock()
        mock_client.get_me = mocker.AsyncMock(return_value=mock_user)
        
        result = await login_as_account(mock_config)
        
        mock_logger.warning.assert_called_once_with(
            "logged in as account, but no username found"
        )
        assert result == mock_client


class TestLoginAsBots:
    @pytest.fixture
    def mock_config(self, mocker):
        config = mocker.Mock(spec=Config)
        config.telegram = mocker.Mock(spec=TelegramConfig)
        config.telegram.api_id = 12345
        config.telegram.api_hash = "test_api_hash"
        config.telegram.bot = mocker.Mock(spec=BotConfig)
        config.telegram.bot.session_file = "/path/to/bots"
        config.telegram.bot.tokens = ["123:token1", "456:token2"]
        config.telegram.bot.token = None  # Using tokens list
        return config

    @pytest.fixture
    def mock_config_single_token(self, mocker):
        config = mocker.Mock(spec=Config)
        config.telegram = mocker.Mock(spec=TelegramConfig)
        config.telegram.api_id = 12345
        config.telegram.api_hash = "test_api_hash"
        config.telegram.bot = mocker.Mock(spec=BotConfig)
        config.telegram.bot.session_file = "/path/to/bots"
        config.telegram.bot.tokens = None
        config.telegram.bot.token = "789:single_token"
        return config

    @pytest.mark.asyncio
    async def test_login_as_bots_multiple_tokens(self, mock_config, mocker):
        mock_clients = [mocker.Mock(spec=TelegramClient), mocker.Mock(spec=TelegramClient)]
        mock_users = [mocker.Mock(spec=tlt.User), mocker.Mock(spec=tlt.User)]
        mock_users[0].username = "bot1"
        mock_users[1].username = "bot2"
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        mock_gather = mocker.patch('asyncio.gather')
        
        mock_session_instances = [mocker.Mock(), mocker.Mock()]
        MockSession.side_effect = mock_session_instances
        
        # Both sessions don't exist
        mock_session_instances[0].get.return_value = None
        mock_session_instances[1].get.return_value = None
        
        MockTelegramClient.side_effect = mock_clients
        
        for i, client in enumerate(mock_clients):
            client.connect = mocker.AsyncMock()
            client.start = mocker.AsyncMock()
            client.get_me = mocker.AsyncMock(return_value=mock_users[i])
            client.session = mocker.Mock()
            client.session.save.return_value = f"session_string_{i}"
            mock_session_instances[i].save_multibot = mocker.Mock()
        
        # Mock gather to return the result after executing the coroutines
        async def mock_gather_func(*coroutines):
            # Execute each coroutine and collect results
            results = []
            for coro in coroutines:
                results.append(await coro)
            return results
        
        mock_gather.side_effect = mock_gather_func
        
        result = await login_as_bots(mock_config)
        
        assert len(result) == 2
        assert result == mock_clients
        
        # Verify both clients were started with their tokens
        mock_clients[0].start.assert_called_once_with(bot_token="123:token1")
        mock_clients[1].start.assert_called_once_with(bot_token="456:token2")

    @pytest.mark.asyncio
    async def test_login_as_bots_single_token(self, mock_config_single_token, mocker):
        mock_client = mocker.Mock(spec=TelegramClient)
        mock_user = mocker.Mock(spec=tlt.User)
        mock_user.username = "singlebot"
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        mock_gather = mocker.patch('asyncio.gather')
        
        mock_session_instance = mocker.Mock()
        MockSession.return_value = mock_session_instance
        mock_session_instance.get.return_value = None
        
        MockTelegramClient.return_value = mock_client
        mock_client.connect = mocker.AsyncMock()
        mock_client.start = mocker.AsyncMock()
        mock_client.get_me = mocker.AsyncMock(return_value=mock_user)
        mock_client.session = mocker.Mock()
        mock_client.session.save.return_value = "session_string"
        mock_session_instance.save_multibot = mocker.Mock()
        
        # Mock gather to return the result after executing the coroutines
        async def mock_gather_func(*coroutines):
            # Execute each coroutine and collect results
            results = []
            for coro in coroutines:
                results.append(await coro)
            return results
        
        mock_gather.side_effect = mock_gather_func
        
        result = await login_as_bots(mock_config_single_token)
        
        assert len(result) == 1
        assert result[0] == mock_client
        mock_client.start.assert_called_once_with(bot_token="789:single_token")

    @pytest.mark.asyncio
    async def test_login_as_bots_with_existing_session(self, mock_config_single_token, mocker):
        mock_client = mocker.Mock(spec=TelegramClient)
        mock_user = mocker.Mock(spec=tlt.User)
        mock_user.username = "existingbot"
        existing_session = mocker.Mock(spec=StringSession)
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        mock_gather = mocker.patch('asyncio.gather')
        
        mock_session_instance = mocker.Mock()
        MockSession.return_value = mock_session_instance
        mock_session_instance.get.return_value = existing_session
        
        MockTelegramClient.return_value = mock_client
        mock_client.connect = mocker.AsyncMock()
        mock_client.start = mocker.AsyncMock()  # Should not be called
        mock_client.get_me = mocker.AsyncMock(return_value=mock_user)
        
        # Mock gather to return the result after executing the coroutines
        async def mock_gather_func(*coroutines):
            # Execute each coroutine and collect results
            results = []
            for coro in coroutines:
                results.append(await coro)
            return results
        
        mock_gather.side_effect = mock_gather_func
        
        result = await login_as_bots(mock_config_single_token)
        
        MockTelegramClient.assert_called_once_with(
            existing_session, 12345, "test_api_hash"
        )
        mock_client.connect.assert_called_once()
        mock_client.start.assert_not_called()  # Should not start if session exists
        assert result[0] == mock_client

    @pytest.mark.asyncio
    async def test_login_as_bots_no_username(self, mock_config_single_token, mocker):
        mock_client = mocker.Mock(spec=TelegramClient)
        mock_user = mocker.Mock(spec=tlt.User)
        mock_user.username = None
        
        MockSession = mocker.patch('tgfs.telegram.impl.telethon.Session')
        MockTelegramClient = mocker.patch('tgfs.telegram.impl.telethon.TelegramClient')
        mock_gather = mocker.patch('asyncio.gather')
        mock_logger = mocker.patch('tgfs.telegram.impl.telethon.logger')
        
        mock_session_instance = mocker.Mock()
        MockSession.return_value = mock_session_instance
        mock_session_instance.get.return_value = None
        
        MockTelegramClient.return_value = mock_client
        mock_client.connect = mocker.AsyncMock()
        mock_client.start = mocker.AsyncMock()
        mock_client.get_me = mocker.AsyncMock(return_value=mock_user)
        mock_client.session = mocker.Mock()
        mock_client.session.save.return_value = "session_string"
        mock_session_instance.save_multibot = mocker.Mock()
        
        # Mock gather to return the result after executing the coroutines
        async def mock_gather_func(*coroutines):
            # Execute each coroutine and collect results
            results = []
            for coro in coroutines:
                results.append(await coro)
            return results
        
        mock_gather.side_effect = mock_gather_func
        
        result = await login_as_bots(mock_config_single_token)
        
        mock_logger.warning.assert_called_once_with(
            "logged in as bot, but no username found"
        )
        assert result[0] == mock_client