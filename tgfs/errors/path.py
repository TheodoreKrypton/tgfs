from http import HTTPStatus

from .base import BusinessError
from .error_code import ErrorCode


class FileOrDirectoryAlreadyExists(BusinessError):
    def __init__(self, path: str):
        message = f"'{path}' already exists"
        super().__init__(
            message=message,
            code=ErrorCode.FILE_OR_DIR_ALREADY_EXISTS,
            cause=message,
            http_error=HTTPStatus.CONFLICT,
        )


class FileOrDirectoryDoesNotExist(BusinessError):
    def __init__(self, path: str):
        message = f"No such file or directory: '{path}'"
        super().__init__(
            message=message,
            code=ErrorCode.FILE_OR_DIR_DOES_NOT_EXIST,
            cause=message,
            http_error=HTTPStatus.NOT_FOUND,
        )


class InvalidName(BusinessError):
    def __init__(self, name: str):
        message = f"Invalid name: '{name}'. Name cannot begin with - or contain /"
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_NAME,
            cause=message,
            http_error=HTTPStatus.BAD_REQUEST,
        )


class InvalidPath(BusinessError):
    def __init__(self, path: str):
        message = (
            f"Path invalid: '{path}'. Path must start with /, and must not end with /"
        )
        super().__init__(
            message=message,
            code=ErrorCode.RELATIVE_PATH,
            cause=message,
            http_error=HTTPStatus.BAD_REQUEST,
        )


class DirectoryIsNotEmpty(BusinessError):
    def __init__(self, path: str):
        message = f"Cannot remove a directory that is not empty: '{path}'"
        super().__init__(
            message=message,
            code=ErrorCode.DIR_IS_NOT_EMPTY,
            cause=message,
            http_error=HTTPStatus.BAD_REQUEST,
        )
