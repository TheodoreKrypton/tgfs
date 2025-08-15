import pytest
from fastapi.testclient import TestClient
from tgfs.app import create_app, cors, READONLY_METHODS
from tgfs.config import Config
from tgfs.core.client import Client


class TestCreateApp:
    @pytest.fixture
    def mock_client(self, mocker):
        client = mocker.Mock(spec=Client)
        client.message_api = mocker.Mock()
        return client

    @pytest.fixture
    def mock_config(self, mocker):
        config = mocker.Mock(spec=Config)
        config.telegram = mocker.Mock()
        config.telegram.private_file_channel = "123456"
        config.tgfs = mocker.Mock()
        config.tgfs.users = {
            "testuser": mocker.Mock(password="testpass", readonly=False)
        }
        return config

    def test_create_app_returns_fastapi(self, mock_client, mock_config, mocker):
        mocker.patch("tgfs.app.create_manager_app")
        mocker.patch("tgfs.app.create_webdav_app")
        app = create_app(mock_client, mock_config)
        assert hasattr(app, "add_middleware")
        assert hasattr(app, "middleware")

    def test_cors_adds_middleware(self):
        from fastapi import FastAPI

        app = FastAPI()
        cors_app = cors(app)
        assert cors_app == app

    def test_readonly_methods_constant(self):
        expected_methods = {"GET", "HEAD", "OPTIONS", "PROPFIND"}
        assert READONLY_METHODS == expected_methods

    def test_app_has_login_endpoint(self, mock_client, mock_config, mocker):
        mock_manager = mocker.patch("tgfs.app.create_manager_app")
        mock_webdav = mocker.patch("tgfs.app.create_webdav_app")
        mock_manager.return_value = mocker.Mock()
        mock_webdav.return_value = mocker.Mock()

        app = create_app(mock_client, mock_config)
        client = TestClient(app)

        # Test OPTIONS request (should pass without auth)
        response = client.options("/")
        assert response.status_code != 401  # Should not require auth

    def test_auth_middleware_basic_auth(self, mock_client, mock_config, mocker):
        mock_manager = mocker.patch("tgfs.app.create_manager_app")
        mock_webdav = mocker.patch("tgfs.app.create_webdav_app")
        mock_auth_basic = mocker.patch("tgfs.app.auth_basic")
        mock_manager.return_value = mocker.Mock()
        mock_webdav.return_value = mocker.Mock()
        mock_user = mocker.Mock(readonly=False)
        mock_auth_basic.return_value = mock_user

        app = create_app(mock_client, mock_config)
        client = TestClient(app)

        # Test with basic auth header
        import base64

        credentials = base64.b64encode(b"user:pass").decode()
        headers = {"Authorization": f"Basic {credentials}"}

        response = client.get("/", headers=headers)
        mock_auth_basic.assert_called_once_with("user", "pass")

    def test_auth_middleware_bearer_auth(self, mock_client, mock_config, mocker):
        mock_manager = mocker.patch("tgfs.app.create_manager_app")
        mock_webdav = mocker.patch("tgfs.app.create_webdav_app")
        mock_auth_bearer = mocker.patch("tgfs.app.auth_bearer")
        mock_manager.return_value = mocker.Mock()
        mock_webdav.return_value = mocker.Mock()
        mock_user = mocker.Mock(readonly=False)
        mock_auth_bearer.return_value = mock_user

        app = create_app(mock_client, mock_config)
        client = TestClient(app)

        headers = {"Authorization": "Bearer testtoken"}
        response = client.get("/", headers=headers)
        mock_auth_bearer.assert_called_once_with("testtoken")

    def test_auth_middleware_missing_header(self, mock_client, mock_config, mocker):
        mock_manager = mocker.patch("tgfs.app.create_manager_app")
        mock_webdav = mocker.patch("tgfs.app.create_webdav_app")
        mock_manager.return_value = mocker.Mock()
        mock_webdav.return_value = mocker.Mock()

        app = create_app(mock_client, mock_config)
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 401
        assert "Authorization header is missing" in response.text

    def test_auth_middleware_unsupported_method(self, mock_client, mock_config, mocker):
        mock_manager = mocker.patch("tgfs.app.create_manager_app")
        mock_webdav = mocker.patch("tgfs.app.create_webdav_app")
        mock_manager.return_value = mocker.Mock()
        mock_webdav.return_value = mocker.Mock()

        app = create_app(mock_client, mock_config)
        client = TestClient(app)

        headers = {"Authorization": "Unsupported token"}
        response = client.get("/", headers=headers)
        assert response.status_code == 401
        assert "Unsupported authentication method" in response.text

    def test_readonly_user_forbidden_on_write_method(
        self, mock_client, mock_config, mocker
    ):
        mock_manager = mocker.patch("tgfs.app.create_manager_app")
        mock_webdav = mocker.patch("tgfs.app.create_webdav_app")
        mock_auth_basic = mocker.patch("tgfs.app.auth_basic")
        mock_manager.return_value = mocker.Mock()
        mock_webdav.return_value = mocker.Mock()
        mock_user = mocker.Mock(readonly=True)
        mock_auth_basic.return_value = mock_user

        app = create_app(mock_client, mock_config)
        client = TestClient(app)

        import base64

        credentials = base64.b64encode(b"user:pass").decode()
        headers = {"Authorization": f"Basic {credentials}"}

        response = client.post("/", headers=headers)
        assert response.status_code == 403
        assert "You do not have permission to perform this action" in response.text

    def test_login_endpoint_success(self, mock_client, mock_config, mocker):
        mock_manager = mocker.patch("tgfs.app.create_manager_app")
        mock_webdav = mocker.patch("tgfs.app.create_webdav_app")
        mock_login = mocker.patch("tgfs.app.login_bearer")
        mock_manager.return_value = mocker.Mock()
        mock_webdav.return_value = mocker.Mock()
        mock_login.return_value = "test_token"

        app = create_app(mock_client, mock_config)
        client = TestClient(app)

        response = client.post(
            "/login", json={"username": "testuser", "password": "testpass"}
        )
        assert response.status_code == 200
        assert response.json() == {"token": "test_token"}
        mock_login.assert_called_once_with("testuser", "testpass")

    def test_login_endpoint_failure(self, mock_client, mock_config, mocker):
        mock_manager = mocker.patch("tgfs.app.create_manager_app")
        mock_webdav = mocker.patch("tgfs.app.create_webdav_app")
        mock_login = mocker.patch("tgfs.app.login_bearer")
        mock_manager.return_value = mocker.Mock()
        mock_webdav.return_value = mocker.Mock()
        mock_login.side_effect = Exception("Invalid credentials")

        app = create_app(mock_client, mock_config)
        client = TestClient(app)

        response = client.post(
            "/login", json={"username": "testuser", "password": "wrongpass"}
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.text
