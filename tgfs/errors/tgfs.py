from .base import BusinessError
from .error_code import ErrorCode


class MetadataNotFound(BusinessError):
    def __init__(self):
        super().__init__(
            message="Metadata not found",
            code=ErrorCode.METADATA_NOT_FOUND,
            cause=None,
        )


class MetadataNotInitialized(BusinessError):
    def __init__(self):
        super().__init__(
            message="Metadata not initialized",
            code=ErrorCode.METADATA_NOT_INITIALIZED,
            cause=None,
        )


class UnDownloadableMessage(BusinessError):
    def __init__(self, message_id: int):
        super().__init__(
            message=f"Message {message_id} does not contain a document",
            code=ErrorCode.UNDOWNLOADABLE_MESSAGE,
            cause=None,
        )
        self.message_id = message_id


class NoPinnedMessage(BusinessError):
    def __init__(self):
        super().__init__(
            message="No pinned message found",
            code=ErrorCode.NO_PINNED_MESSAGE,
            cause=None,
        )


class PinnedMessageNotSupported(BusinessError):
    def __init__(self):
        super().__init__(
            message="Pinned message is not supported because account api is not configured. Use metadata by Github repo instead.",
            code=ErrorCode.PINNED_MESSAGE_NOT_SUPPORTED,
            cause=None,
        )


class TaskCancelled(BusinessError):
    def __init__(self, file_name: str):
        super().__init__(
            message=f"Task for {file_name} has been cancelled",
            code=ErrorCode.TASK_CANCELLED,
            cause=None,
        )


class LoginFailed(BusinessError):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code=ErrorCode.LOGIN_FAILED,
            cause=None,
        )


class DuplicatedChannelIdOrName(BusinessError):
    def __init__(self, channel_id_or_name: str):
        super().__init__(
            message=f"Channel ID or name {channel_id_or_name} is already used",
            code=ErrorCode.DUPLICATED_CHANNEL_ID_OR_NAME,
            cause=None,
        )
