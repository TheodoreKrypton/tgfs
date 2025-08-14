import pytest
from tgfs.config import (
    WebDAVConfig,
    ManagerConfig,
    DownloadConfig,
    UserConfig,
    JWTConfig,
    ServerConfig,
    TGFSConfig,
    Config,
    GithubRepoConfig,
    MetadataConfig,
    MetadataType,
)


class TestWebDAVConfig:
    def test_from_dict(self):
        data = {"host": "localhost", "port": 8080, "path": "/webdav"}
        config = WebDAVConfig.from_dict(data)

        assert config.host == "localhost"
        assert config.port == 8080
        assert config.path == "/webdav"


class TestManagerConfig:
    def test_from_dict(self):
        data = {"host": "0.0.0.0", "port": 9000}
        config = ManagerConfig.from_dict(data)

        assert config.host == "0.0.0.0"
        assert config.port == 9000


class TestDownloadConfig:
    def test_from_dict(self):
        data = {"chunk_size_kb": 1024}
        config = DownloadConfig.from_dict(data)

        assert config.chunk_size_kb == 1024


class TestUserConfig:
    def test_from_dict_readonly_false(self):
        data = {"password": "secret", "readonly": False}
        config = UserConfig.from_dict(data)

        assert config.password == "secret"
        assert config.readonly is False

    def test_from_dict_readonly_default_false(self):
        data = {"password": "secret"}
        config = UserConfig.from_dict(data)

        assert config.password == "secret"
        assert config.readonly is False

    def test_from_dict_readonly_true(self):
        data = {"password": "secret", "readonly": True}
        config = UserConfig.from_dict(data)

        assert config.password == "secret"
        assert config.readonly is True


class TestJWTConfig:
    def test_from_dict(self):
        data = {"secret": "jwt_secret", "algorithm": "HS256", "life": 3600}
        config = JWTConfig.from_dict(data)

        assert config.secret == "jwt_secret"
        assert config.algorithm == "HS256"
        assert config.life == 3600


class TestServerConfig:
    def test_from_dict(self):
        data = {"host": "127.0.0.1", "port": 8000}
        config = ServerConfig.from_dict(data)

        assert config.host == "127.0.0.1"
        assert config.port == 8000


class TestTGFSConfig:
    def test_from_dict_minimal(self):
        data = {
            "users": {},
            "download": {"chunk_size_kb": 512},
            "jwt": {"secret": "test", "algorithm": "HS256", "life": 1800},
            "server": {"host": "localhost", "port": 3000},
        }
        config = TGFSConfig.from_dict(data)

        assert config.users == {}
        assert config.download.chunk_size_kb == 512
        assert config.jwt.secret == "test"
        assert config.server.host == "localhost"

    def test_from_dict_with_users(self):
        data = {
            "users": {
                "admin": {"password": "admin123", "readonly": False},
                "viewer": {"password": "view123", "readonly": True},
            },
            "download": {"chunk_size_kb": 512},
            "jwt": {"secret": "test", "algorithm": "HS256", "life": 1800},
            "server": {"host": "localhost", "port": 3000},
        }
        config = TGFSConfig.from_dict(data)

        assert "admin" in config.users
        assert "viewer" in config.users
        assert config.users["admin"].password == "admin123"
        assert config.users["admin"].readonly is False
        assert config.users["viewer"].readonly is True

    def test_from_dict_no_users(self):
        data = {
            "users": None,
            "download": {"chunk_size_kb": 512},
            "jwt": {"secret": "test", "algorithm": "HS256", "life": 1800},
            "server": {"host": "localhost", "port": 3000},
        }
        config = TGFSConfig.from_dict(data)

        assert config.users == {}


class TestGithubRepoConfig:
    def test_from_dict(self):
        data = {"repo": "owner/repo", "commit": "main", "access_token": "token123"}
        config = GithubRepoConfig.from_dict(data)

        assert config.repo == "owner/repo"
        assert config.commit == "main"
        assert config.access_token == "token123"


class TestMetadataConfig:
    def test_from_dict_none(self):
        config = MetadataConfig.from_dict(None)

        assert config.type == MetadataType.PINNED_MESSAGE
        assert config.github_repo is None

    def test_from_dict_pinned_message(self):
        data = {"type": "pinned_message"}
        config = MetadataConfig.from_dict(data)

        assert config.type == MetadataType.PINNED_MESSAGE
        assert config.github_repo is None

    def test_from_dict_github_repo(self):
        data = {
            "type": "github_repo",
            "github_repo": {
                "repo": "owner/repo",
                "commit": "main",
                "access_token": "token123",
            },
        }
        config = MetadataConfig.from_dict(data)

        assert config.type == MetadataType.GITHUB_REPO
        assert config.github_repo is not None
        assert config.github_repo.repo == "owner/repo"

    def test_from_dict_unknown_type(self):
        data = {"type": "unknown_type"}

        with pytest.raises(ValueError, match="Unknown metadata type: unknown_type"):
            MetadataConfig.from_dict(data)


class TestConfig:
    def test_from_dict(self):
        data = {
            "telegram": {
                "api_id": 12345,
                "api_hash": "hash123",
                "bot": {"token": "bot_token", "session_file": "bot.session"},
                "account": {"session_file": "account.session"},
                "login_timeout": 30000,
                "private_file_channel": 123456,
                "public_file_channel": 654321,
            },
            "tgfs": {
                "users": {},
                "download": {"chunk_size_kb": 1024},
                "jwt": {"secret": "jwt_secret", "algorithm": "HS256", "life": 3600},
                "server": {"host": "0.0.0.0", "port": 8080},
            },
        }
        config = Config.from_dict(data)

        assert config.telegram.api_id == 12345
        assert config.tgfs.download.chunk_size_kb == 1024


class TestConfigFunctions:
    def test_get_config_loads_file(self, mocker):
        mock_open = mocker.patch("tgfs.config.open")
        mock_yaml_load = mocker.patch("tgfs.config.yaml.safe_load")
        mocker.patch("tgfs.config.__config", None)
        from tgfs.config import get_config

        mock_yaml_load.return_value = {
            "telegram": {
                "api_id": 12345,
                "api_hash": "hash123",
                "bot": {"token": "bot_token", "session_file": "bot.session"},
                "account": {"session_file": "account.session"},
                "login_timeout": 30000,
                "private_file_channel": 123456,
                "public_file_channel": 654321,
            },
            "tgfs": {
                "users": {},
                "download": {"chunk_size_kb": 1024},
                "jwt": {"secret": "jwt_secret", "algorithm": "HS256", "life": 3600},
                "server": {"host": "0.0.0.0", "port": 8080},
            },
        }

        config = get_config()

        mock_open.assert_called_once()
        mock_yaml_load.assert_called_once()
        assert config.telegram.api_id == 12345
