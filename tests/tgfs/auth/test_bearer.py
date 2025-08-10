import pytest
import time
import jwt
from tgfs.auth.bearer import login, authenticate, JWTPayload
from tgfs.auth.user import AdminUser, ReadonlyUser
from tgfs.errors import LoginFailed


class TestBearerAuth:
    def test_login_anonymous_when_no_users(self, mocker):
        # Setup config with no users
        mock_config = mocker.Mock()
        mock_config.tgfs.users = {}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        
        mocker.patch('tgfs.auth.bearer.config', mock_config)
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        
        token = login("testuser", "testpass")
        
        # Decode and verify the token
        payload = jwt.decode(token, key="test_secret", algorithms=["HS256"])
        assert payload["username"] == "anonymous"
        assert payload["readonly"] is True
        assert "exp" in payload

    def test_login_anonymous_disabled(self, mocker):
        # Setup config with users (anonymous disabled)
        mock_user = mocker.Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = False
        
        mock_config = mocker.Mock()
        mock_config.tgfs.users = {"testuser": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        
        mocker.patch('tgfs.auth.bearer.config', mock_config)
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        
        # Empty username should raise LoginFailed
        with pytest.raises(LoginFailed, match="Anonymous login is disabled"):
            login("", "anypass")

    def test_login_valid_user(self, mocker):
        # Setup config with valid user
        mock_user = mocker.Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = False
        
        mock_config = mocker.Mock()
        mock_config.tgfs.users = {"testuser": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        
        mocker.patch('tgfs.auth.bearer.config', mock_config)
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        
        token = login("testuser", "correctpass")
        
        # Decode and verify the token
        payload = jwt.decode(token, key="test_secret", algorithms=["HS256"])
        assert payload["username"] == "testuser"
        assert payload["readonly"] is False
        assert "exp" in payload

    def test_login_invalid_user(self, mocker):
        # Setup config with users
        mock_user = mocker.Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = False
        
        mock_config = mocker.Mock()
        mock_config.tgfs.users = {"testuser": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        
        mocker.patch('tgfs.auth.bearer.config', mock_config)
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        
        # Non-existent user should raise LoginFailed
        with pytest.raises(LoginFailed, match="No such user \\(nonexistent\\) or password incorrect"):
            login("nonexistent", "anypass")

    def test_login_wrong_password(self, mocker):
        # Setup config with valid user
        mock_user = mocker.Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = False
        
        mock_config = mocker.Mock()
        mock_config.tgfs.users = {"testuser": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        
        mocker.patch('tgfs.auth.bearer.config', mock_config)
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        
        # Wrong password should raise LoginFailed
        with pytest.raises(LoginFailed, match="No such user \\(testuser\\) or password incorrect"):
            login("testuser", "wrongpass")

    def test_login_readonly_user(self, mocker):
        # Setup config with readonly user
        mock_user = mocker.Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = True
        
        mock_config = mocker.Mock()
        mock_config.tgfs.users = {"readonly_user": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        
        mocker.patch('tgfs.auth.bearer.config', mock_config)
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        
        token = login("readonly_user", "correctpass")
        
        # Decode and verify the token
        payload = jwt.decode(token, key="test_secret", algorithms=["HS256"])
        assert payload["username"] == "readonly_user"
        assert payload["readonly"] is True

    def test_authenticate_admin_user(self, mocker):
        mock_config = mocker.Mock()
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        
        # Create a valid admin token
        payload = JWTPayload(
            username="admin",
            exp=int(time.time()) + 3600,
            readonly=False
        )
        token = jwt.encode(dict(payload), key="test_secret", algorithm="HS256")
        
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        user = authenticate(token)
        
        assert isinstance(user, AdminUser)
        assert user.username == "admin"

    def test_authenticate_readonly_user(self, mocker):
        mock_config = mocker.Mock()
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        
        # Create a valid readonly token
        payload = JWTPayload(
            username="readonly",
            exp=int(time.time()) + 3600,
            readonly=True
        )
        token = jwt.encode(dict(payload), key="test_secret", algorithm="HS256")
        
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        user = authenticate(token)
        
        assert isinstance(user, ReadonlyUser)
        assert user.username == "readonly"

    def test_authenticate_invalid_token(self, mocker):
        mock_config = mocker.Mock()
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        
        # Invalid token should raise jwt.DecodeError
        with pytest.raises(jwt.DecodeError):
            authenticate("invalid.token.here")

    def test_authenticate_expired_token(self, mocker):
        mock_config = mocker.Mock()
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        
        # Create an expired token
        payload = JWTPayload(
            username="admin",
            exp=int(time.time()) - 3600,  # Expired 1 hour ago
            readonly=False
        )
        token = jwt.encode(dict(payload), key="test_secret", algorithm="HS256")
        
        mocker.patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt)
        
        # Expired token should raise jwt.ExpiredSignatureError
        with pytest.raises(jwt.ExpiredSignatureError):
            authenticate(token)