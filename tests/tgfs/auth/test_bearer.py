import pytest
import time
from unittest.mock import Mock, patch
import jwt
from tgfs.auth.bearer import login, authenticate, JWTPayload
from tgfs.auth.user import AdminUser, ReadonlyUser
from tgfs.errors import LoginFailed


class TestBearerAuth:
    @patch('tgfs.auth.bearer.get_config')
    def test_login_anonymous_when_no_users(self, mock_get_config):
        # Setup config with no users
        mock_config = Mock()
        mock_config.tgfs.users = {}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        mock_get_config.return_value = mock_config
        
        with patch('tgfs.auth.bearer.config', mock_config):
            with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
                token = login("testuser", "testpass")
        
        # Decode and verify the token
        payload = jwt.decode(token, key="test_secret", algorithms=["HS256"])
        assert payload["username"] == "anonymous"
        assert payload["readonly"] is True
        assert "exp" in payload

    @patch('tgfs.auth.bearer.get_config')
    def test_login_anonymous_disabled(self, mock_get_config):
        # Setup config with users (anonymous disabled)
        mock_user = Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = False
        
        mock_config = Mock()
        mock_config.tgfs.users = {"testuser": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        mock_get_config.return_value = mock_config
        
        with patch('tgfs.auth.bearer.config', mock_config):
            with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
                # Empty username should raise LoginFailed
                with pytest.raises(LoginFailed, match="Anonymous login is disabled"):
                    login("", "anypass")

    @patch('tgfs.auth.bearer.get_config')
    def test_login_valid_user(self, mock_get_config):
        # Setup config with valid user
        mock_user = Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = False
        
        mock_config = Mock()
        mock_config.tgfs.users = {"testuser": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        mock_get_config.return_value = mock_config
        
        with patch('tgfs.auth.bearer.config', mock_config):
            with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
                token = login("testuser", "correctpass")
        
        # Decode and verify the token
        payload = jwt.decode(token, key="test_secret", algorithms=["HS256"])
        assert payload["username"] == "testuser"
        assert payload["readonly"] is False
        assert "exp" in payload

    @patch('tgfs.auth.bearer.get_config')
    def test_login_invalid_user(self, mock_get_config):
        # Setup config with users
        mock_user = Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = False
        
        mock_config = Mock()
        mock_config.tgfs.users = {"testuser": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        mock_get_config.return_value = mock_config
        
        with patch('tgfs.auth.bearer.config', mock_config):
            with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
                # Non-existent user should raise LoginFailed
                with pytest.raises(LoginFailed, match="No such user \\(nonexistent\\) or password incorrect"):
                    login("nonexistent", "anypass")

    @patch('tgfs.auth.bearer.get_config')
    def test_login_wrong_password(self, mock_get_config):
        # Setup config with valid user
        mock_user = Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = False
        
        mock_config = Mock()
        mock_config.tgfs.users = {"testuser": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        mock_get_config.return_value = mock_config
        
        with patch('tgfs.auth.bearer.config', mock_config):
            with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
                # Wrong password should raise LoginFailed
                with pytest.raises(LoginFailed, match="No such user \\(testuser\\) or password incorrect"):
                    login("testuser", "wrongpass")

    @patch('tgfs.auth.bearer.get_config')
    def test_login_readonly_user(self, mock_get_config):
        # Setup config with readonly user
        mock_user = Mock()
        mock_user.password = "correctpass"
        mock_user.readonly = True
        
        mock_config = Mock()
        mock_config.tgfs.users = {"readonly_user": mock_user}
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_config.tgfs.jwt.life = 3600
        mock_get_config.return_value = mock_config
        
        with patch('tgfs.auth.bearer.config', mock_config):
            with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
                token = login("readonly_user", "correctpass")
        
        # Decode and verify the token
        payload = jwt.decode(token, key="test_secret", algorithms=["HS256"])
        assert payload["username"] == "readonly_user"
        assert payload["readonly"] is True

    @patch('tgfs.auth.bearer.get_config')
    def test_authenticate_admin_user(self, mock_get_config):
        mock_config = Mock()
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_get_config.return_value = mock_config
        
        # Create a valid admin token
        payload = JWTPayload(
            username="admin",
            exp=int(time.time()) + 3600,
            readonly=False
        )
        token = jwt.encode(dict(payload), key="test_secret", algorithm="HS256")
        
        with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
            user = authenticate(token)
        
        assert isinstance(user, AdminUser)
        assert user.username == "admin"

    @patch('tgfs.auth.bearer.get_config')
    def test_authenticate_readonly_user(self, mock_get_config):
        mock_config = Mock()
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_get_config.return_value = mock_config
        
        # Create a valid readonly token
        payload = JWTPayload(
            username="readonly",
            exp=int(time.time()) + 3600,
            readonly=True
        )
        token = jwt.encode(dict(payload), key="test_secret", algorithm="HS256")
        
        with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
            user = authenticate(token)
        
        assert isinstance(user, ReadonlyUser)
        assert user.username == "readonly"

    @patch('tgfs.auth.bearer.get_config')
    def test_authenticate_invalid_token(self, mock_get_config):
        mock_config = Mock()
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_get_config.return_value = mock_config
        
        with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
            # Invalid token should raise jwt.DecodeError
            with pytest.raises(jwt.DecodeError):
                authenticate("invalid.token.here")

    @patch('tgfs.auth.bearer.get_config')
    def test_authenticate_expired_token(self, mock_get_config):
        mock_config = Mock()
        mock_config.tgfs.jwt.secret = "test_secret"
        mock_config.tgfs.jwt.algorithm = "HS256"
        mock_get_config.return_value = mock_config
        
        # Create an expired token
        payload = JWTPayload(
            username="admin",
            exp=int(time.time()) - 3600,  # Expired 1 hour ago
            readonly=False
        )
        token = jwt.encode(dict(payload), key="test_secret", algorithm="HS256")
        
        with patch('tgfs.auth.bearer.jwt_config', mock_config.tgfs.jwt):
            # Expired token should raise jwt.ExpiredSignatureError
            with pytest.raises(jwt.ExpiredSignatureError):
                authenticate(token)