class User:
    readonly = True

    def __init__(self, username: str):
        self.username = username


class ReadonlyUser(User):
    pass


class AdminUser(ReadonlyUser):
    readonly = False
