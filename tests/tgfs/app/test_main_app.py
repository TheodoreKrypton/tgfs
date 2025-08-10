import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from tgfs.app import create_app, cors, READONLY_METHODS
from tgfs.config import Config
from tgfs.core.client import Client


class TestCreateApp:
    @pytest.fixture
    def mock_client(self):
        client = Mock(spec=Client)
        client.message_api = Mock()
        return client

    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=Config)
        config.telegram = Mock()
        config.telegram.private_file_channel = "123456"
        config.tgfs = Mock()
        config.tgfs.users = {
            "testuser": Mock(password="testpass", readonly=False)
        }
        return config

    def test_create_app_returns_fastapi(self, mock_client, mock_config):
        with patch('tgfs.app.create_manager_app'), patch('tgfs.app.create_webdav_app'):
            app = create_app(mock_client, mock_config)
            assert hasattr(app, 'add_middleware')
            assert hasattr(app, 'middleware')

    def test_cors_adds_middleware(self):
        from fastapi import FastAPI
        app = FastAPI()
        cors_app = cors(app)
        assert cors_app == app

    def test_readonly_methods_constant(self):
        expected_methods = {"GET", "HEAD", "OPTIONS", "PROPFIND"}
        assert READONLY_METHODS == expected_methods

    @patch('tgfs.app.create_manager_app')
    @patch('tgfs.app.create_webdav_app')
    def test_app_has_login_endpoint(self, mock_webdav, mock_manager, mock_client, mock_config):
        mock_manager.return_value = Mock()
        mock_webdav.return_value = Mock()
        
        app = create_app(mock_client, mock_config)
        client = TestClient(app)
        
        # Test OPTIONS request (should pass without auth)
        response = client.options("/")
        assert response.status_code != 401  # Should not require auth

    @patch('tgfs.app.create_manager_app')
    @patch('tgfs.app.create_webdav_app')
    @patch('tgfs.app.auth_basic')
    def test_auth_middleware_basic_auth(self, mock_auth_basic, mock_webdav, mock_manager, mock_client, mock_config):
        mock_manager.return_value = Mock()
        mock_webdav.return_value = Mock()
        mock_user = Mock(readonly=False)
        mock_auth_basic.return_value = mock_user
        
        app = create_app(mock_client, mock_config)
        client = TestClient(app)
        
        # Test with basic auth header
        import base64
        credentials = base64.b64encode(b"user:pass").decode()
        headers = {"Authorization": f"Basic {credentials}"}
        
        response = client.get("/", headers=headers)
        mock_auth_basic.assert_called_once_with("user", "pass")

    @patch('tgfs.app.create_manager_app')
    @patch('tgfs.app.create_webdav_app')
    @patch('tgfs.app.auth_bearer')
    def test_auth_middleware_bearer_auth(self, mock_auth_bearer, mock_webdav, mock_manager, mock_client, mock_config):
        mock_manager.return_value = Mock()
        mock_webdav.return_value = Mock()
        mock_user = Mock(readonly=False)
        mock_auth_bearer.return_value = mock_user
        
        app = create_app(mock_client, mock_config)
        client = TestClient(app)
        
        headers = {"Authorization": "Bearer testtoken"}
        response = client.get("/", headers=headers)
        mock_auth_bearer.assert_called_once_with("testtoken")

    @patch('tgfs.app.create_manager_app')
    @patch('tgfs.app.create_webdav_app')
    def test_auth_middleware_missing_header(self, mock_webdav, mock_manager, mock_client, mock_config):
        mock_manager.return_value = Mock()
        mock_webdav.return_value = Mock()
        
        app = create_app(mock_client, mock_config)
        client = TestClient(app)
        
        response = client.get("/")
        assert response.status_code == 401
        assert "Authorization header is missing" in response.text

    @patch('tgfs.app.create_manager_app')
    @patch('tgfs.app.create_webdav_app')
    def test_auth_middleware_unsupported_method(self, mock_webdav, mock_manager, mock_client, mock_config):
        mock_manager.return_value = Mock()
        mock_webdav.return_value = Mock()
        
        app = create_app(mock_client, mock_config)
        client = TestClient(app)
        
        headers = {"Authorization": "Unsupported token"}
        response = client.get("/", headers=headers)
        assert response.status_code == 401
        assert "Unsupported authentication method" in response.text

    @patch('tgfs.app.create_manager_app')
    @patch('tgfs.app.create_webdav_app')
    @patch('tgfs.app.auth_basic')
    def test_readonly_user_forbidden_on_write_method(self, mock_auth_basic, mock_webdav, mock_manager, mock_client, mock_config):
        mock_manager.return_value = Mock()
        mock_webdav.return_value = Mock()
        mock_user = Mock(readonly=True)
        mock_auth_basic.return_value = mock_user
        
        app = create_app(mock_client, mock_config)
        client = TestClient(app)
        
        import base64
        credentials = base64.b64encode(b"user:pass").decode()
        headers = {"Authorization": f"Basic {credentials}"}
        
        response = client.post("/", headers=headers)
        assert response.status_code == 403
        assert "You do not have permission to perform this action" in response.text

    @patch('tgfs.app.create_manager_app')
    @patch('tgfs.app.create_webdav_app')
    @patch('tgfs.app.login_bearer')
    def test_login_endpoint_success(self, mock_login, mock_webdav, mock_manager, mock_client, mock_config):
        mock_manager.return_value = Mock()
        mock_webdav.return_value = Mock()
        mock_login.return_value = "test_token"
        
        app = create_app(mock_client, mock_config)
        client = TestClient(app)
        
        response = client.post("/login", json={"username": "testuser", "password": "testpass"})
        assert response.status_code == 200
        assert response.json() == {"token": "test_token"}
        mock_login.assert_called_once_with("testuser", "testpass")

    @patch('tgfs.app.create_manager_app')
    @patch('tgfs.app.create_webdav_app')
    @patch('tgfs.app.login_bearer')
    def test_login_endpoint_failure(self, mock_login, mock_webdav, mock_manager, mock_client, mock_config):
        mock_manager.return_value = Mock()
        mock_webdav.return_value = Mock()
        mock_login.side_effect = Exception("Invalid credentials")
        
        app = create_app(mock_client, mock_config)
        client = TestClient(app)
        
        response = client.post("/login", json={"username": "testuser", "password": "wrongpass"})
        assert response.status_code == 401
        assert "Invalid credentials" in response.text