from tgfs.errors.base import BusinessError
from tgfs.errors.error_code import ErrorCode


class MetadataNotFound(BusinessError):
    def __init__(self):
        super().__init__(
            message="Metadata not found",
            code=ErrorCode.METADATA_NOT_FOUND,
            cause=None,
        )
