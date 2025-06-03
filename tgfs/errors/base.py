from http import HTTPStatus
from typing import Iterable

from .error_code import ErrorCode


class TechnicalError(Exception):
    def __init__(
        self,
        message: str,
        cause=None,
        http_error: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
    ):
        super().__init__(message)
        self.cause = cause
        self.http_error = http_error


class BusinessError(TechnicalError):
    def __init__(
        self,
        message: str,
        code: ErrorCode,
        cause,
        http_error: HTTPStatus = HTTPStatus.BAD_REQUEST,
    ):
        super().__init__(message, cause, http_error)
        self.code = code


class AggregatedError(Exception):
    def __init__(self, errors: Iterable[Exception]):
        super("\n".join(str(e) for e in errors))
