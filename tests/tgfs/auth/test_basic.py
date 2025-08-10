import pytest
from unittest.mock import Mock, patch
from tgfs.errors.tgfs import LoginFailed


class TestBasicAuth:
    @patch('tgfs.auth.basic.config')
    def test_authenticate_no_users_returns_anonymous(self, mock_config):
        from tgfs.auth.basic import authenticate
        from tgfs.auth.user import ReadonlyUser
        mock_config.tgfs.users = None
        
        user = authenticate("any_user", "any_password")
        
        assert isinstance(user, ReadonlyUser)
        assert user.username == "anonymous"

    @patch('tgfs.auth.basic.config')
    def test_authenticate_no_username_raises_error(self, mock_config):
        from tgfs.auth.basic import authenticate
        mock_user_config = Mock()
        mock_config.tgfs.users = {"test": mock_user_config}
        
        with pytest.raises(LoginFailed, match="Anonymous login is disabled"):
            authenticate("", "password")

    @patch('tgfs.auth.basic.config')
    def test_authenticate_valid_admin_user(self, mock_config):
        from tgfs.auth.basic import authenticate
        from tgfs.auth.user import AdminUser
        mock_user_config = Mock()
        mock_user_config.password = "correct_password"
        mock_user_config.readonly = False
        mock_config.tgfs.users = {"admin": mock_user_config}
        
        user = authenticate("admin", "correct_password")
        
        assert isinstance(user, AdminUser)
        assert user.username == "admin"
        assert user.readonly is False

    @patch('tgfs.auth.basic.config')
    def test_authenticate_valid_readonly_user(self, mock_config):
        from tgfs.auth.basic import authenticate
        from tgfs.auth.user import ReadonlyUser
        mock_user_config = Mock()
        mock_user_config.password = "correct_password"
        mock_user_config.readonly = True
        mock_config.tgfs.users = {"readonly": mock_user_config}
        
        user = authenticate("readonly", "correct_password")
        
        assert isinstance(user, ReadonlyUser)
        assert user.username == "readonly"
        assert user.readonly is True

    @patch('tgfs.auth.basic.config')
    def test_authenticate_invalid_username(self, mock_config):
        from tgfs.auth.basic import authenticate
        mock_user_config = Mock()
        mock_user_config.password = "correct_password"
        mock_config.tgfs.users = {"valid_user": mock_user_config}
        
        with pytest.raises(LoginFailed, match="No such user \\(invalid_user\\) or password is incorrect"):
            authenticate("invalid_user", "any_password")

    @patch('tgfs.auth.basic.config')
    def test_authenticate_invalid_password(self, mock_config):
        from tgfs.auth.basic import authenticate
        mock_user_config = Mock()
        mock_user_config.password = "correct_password"
        mock_config.tgfs.users = {"valid_user": mock_user_config}
        
        with pytest.raises(LoginFailed, match="No such user \\(valid_user\\) or password is incorrect"):
            authenticate("valid_user", "wrong_password")