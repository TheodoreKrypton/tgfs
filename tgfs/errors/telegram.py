from abc import ABCMeta
from http import HTTPStatus

from .base import BusinessError
from .error_code import ErrorCode


class TelegramError(BusinessError, metaclass=ABCMeta):
    pass


class FileSizeTooLarge(TelegramError):
    def __init__(self, size: int):
        message = f"File size {size} exceeds Telegram's limit."
        super().__init__(
            message=message,
            code=ErrorCode.FILE_SIZE_TOO_LARGE,
            cause=message,
            http_error=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        )


class MessageNotFound(TelegramError):
    def __init__(self, message_id: int):
        message = f"Message with ID {message_id} not found."
        super().__init__(
            message=message,
            code=ErrorCode.MESSAGE_NOT_FOUND,
            cause=message,
            http_error=HTTPStatus.NOT_FOUND,
        )
