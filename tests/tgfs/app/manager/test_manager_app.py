import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from tgfs.app.manager.app import create_manager_app
from tgfs.config import Config
from tgfs.core.client import Client
from tgfs.reqres import MessageRespWithDocument


class TestManagerApp:
    @pytest.fixture
    def mock_client(self):
        client = Mock(spec=Client)
        client.message_api = Mock()
        client.message_api.get_messages = AsyncMock()
        return client

    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=Config)
        config.telegram = Mock()
        config.telegram.private_file_channel = "123456"
        return config

    @pytest.fixture
    def manager_app(self, mock_client, mock_config):
        return create_manager_app(mock_client, mock_config)

    def test_create_manager_app_returns_fastapi(self, mock_client, mock_config):
        app = create_manager_app(mock_client, mock_config)
        assert hasattr(app, 'get')
        assert hasattr(app, 'post')
        assert hasattr(app, 'delete')

    @patch('tgfs.app.manager.app.task_store')
    @pytest.mark.asyncio
    async def test_get_tasks_all(self, mock_task_store, manager_app):
        mock_tasks = [Mock(to_dict=Mock(return_value={"id": "1", "path": "/test"}))]
        mock_task_store.get_all_tasks = AsyncMock(return_value=mock_tasks)
        
        client = TestClient(manager_app)
        response = client.get("/tasks")
        
        assert response.status_code == 200
        assert response.json() == [{"id": "1", "path": "/test"}]
        mock_task_store.get_all_tasks.assert_called_once()

    @patch('tgfs.app.manager.app.task_store')
    @pytest.mark.asyncio
    async def test_get_tasks_filtered_by_path(self, mock_task_store, manager_app):
        mock_tasks = [Mock(to_dict=Mock(return_value={"id": "2", "path": "/specific"}))]
        mock_task_store.get_tasks_under_path = AsyncMock(return_value=mock_tasks)
        
        client = TestClient(manager_app)
        response = client.get("/tasks?path=/specific")
        
        assert response.status_code == 200
        assert response.json() == [{"id": "2", "path": "/specific"}]
        mock_task_store.get_tasks_under_path.assert_called_once_with("/specific")

    @patch('tgfs.app.manager.app.task_store')
    @pytest.mark.asyncio
    async def test_get_task_found(self, mock_task_store, manager_app):
        mock_task = Mock(to_dict=Mock(return_value={"id": "task123", "status": "running"}))
        mock_task_store.get_task = AsyncMock(return_value=mock_task)
        
        client = TestClient(manager_app)
        response = client.get("/tasks/task123")
        
        assert response.status_code == 200
        assert response.json() == {"id": "task123", "status": "running"}
        mock_task_store.get_task.assert_called_once_with("task123")

    @patch('tgfs.app.manager.app.task_store')
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, mock_task_store, manager_app):
        mock_task_store.get_task = AsyncMock(return_value=None)
        
        client = TestClient(manager_app)
        response = client.get("/tasks/nonexistent")
        
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    @patch('tgfs.app.manager.app.task_store')
    @pytest.mark.asyncio
    async def test_delete_task_success(self, mock_task_store, manager_app):
        mock_task_store.remove_task = AsyncMock(return_value=True)
        
        client = TestClient(manager_app)
        response = client.delete("/tasks/task123")
        
        assert response.status_code == 200
        assert response.json() == {"message": "Task deleted successfully"}
        mock_task_store.remove_task.assert_called_once_with("task123")

    @patch('tgfs.app.manager.app.task_store')
    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, mock_task_store, manager_app):
        mock_task_store.remove_task = AsyncMock(return_value=False)
        
        client = TestClient(manager_app)
        response = client.delete("/tasks/nonexistent")
        
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_telegram_message_success(self, mock_client, mock_config):
        # Mock the message response
        mock_message = Mock()
        mock_message.message_id = 456
        mock_message.document = Mock(size=1024, mime_type="text/plain")
        mock_message.text = "Test caption"
        mock_client.message_api.get_messages.return_value = [mock_message]
        
        app = create_manager_app(mock_client, mock_config)
        client = TestClient(app)
        
        response = client.get("/message/123456/456")
        
        assert response.status_code == 200
        expected = {
            "id": 456,
            "file_size": 1024,
            "caption": "Test caption",
            "mime_type": "text/plain"
        }
        assert response.json() == expected
        mock_client.message_api.get_messages.assert_called_once_with([456])

    @pytest.mark.asyncio
    async def test_get_telegram_message_wrong_channel(self, mock_client, mock_config):
        app = create_manager_app(mock_client, mock_config)
        client = TestClient(app)
        
        response = client.get("/message/999999/456")
        
        assert response.status_code == 400
        assert "not in the configured file channel" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_telegram_message_not_found(self, mock_client, mock_config):
        mock_client.message_api.get_messages.return_value = [None]
        
        app = create_manager_app(mock_client, mock_config)
        client = TestClient(app)
        
        response = client.get("/message/123456/456")
        
        assert response.status_code == 404
        assert "Message 456 not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_telegram_message_no_document(self, mock_client, mock_config):
        mock_message = Mock()
        mock_message.message_id = 456
        mock_message.document = None
        mock_client.message_api.get_messages.return_value = [mock_message]
        
        app = create_manager_app(mock_client, mock_config)
        client = TestClient(app)
        
        response = client.get("/message/123456/456")
        
        assert response.status_code == 400
        assert "does not contain a document" in response.json()["detail"]

    @patch('tgfs.app.manager.app.fs_cache')
    @patch('tgfs.app.manager.app.Ops')
    @pytest.mark.asyncio
    async def test_import_telegram_message_success(self, mock_ops_class, mock_fs_cache, mock_client, mock_config):
        # Mock the message response
        mock_message = Mock()
        mock_message.message_id = 456
        mock_message.document = Mock(size=1024, mime_type="text/plain")
        mock_message.text = "Test file"
        mock_client.message_api.get_messages.return_value = [mock_message]
        
        # Mock Ops
        mock_ops = Mock()
        mock_ops.import_from_existing_file_message = AsyncMock()
        mock_ops_class.return_value = mock_ops
        
        app = create_manager_app(mock_client, mock_config)
        client = TestClient(app)
        
        payload = {
            "directory": "/uploads",
            "name": "test.txt",
            "channel_id": 123456,
            "message_id": 456
        }
        
        response = client.post("/import", json=payload)
        
        assert response.status_code == 200
        assert response.json() == {"message": "Document imported successfully"}
        mock_fs_cache.reset_parent.assert_called_once_with("/uploads/test.txt")
        mock_ops.import_from_existing_file_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_telegram_message_wrong_channel(self, mock_client, mock_config):
        app = create_manager_app(mock_client, mock_config)
        client = TestClient(app)
        
        payload = {
            "directory": "/uploads",
            "name": "test.txt", 
            "channel_id": 999999,
            "message_id": 456
        }
        
        response = client.post("/import", json=payload)
        
        assert response.status_code == 400
        assert "not in the configured file channel" in response.json()["detail"]