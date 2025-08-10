from tgfs.auth.user import User, ReadonlyUser, AdminUser


class TestUser:
    def test_user_init(self):
        user = User("testuser")
        assert user.username == "testuser"
        assert user.readonly is True

    def test_readonly_user_init(self):
        user = ReadonlyUser("readonly_user")
        assert user.username == "readonly_user"
        assert user.readonly is True

    def test_admin_user_init(self):
        user = AdminUser("admin_user")
        assert user.username == "admin_user"
        assert user.readonly is False

    def test_user_inheritance(self):
        readonly_user = ReadonlyUser("test")
        admin_user = AdminUser("test")
        
        assert isinstance(readonly_user, User)
        assert isinstance(admin_user, ReadonlyUser)
        assert isinstance(admin_user, User)