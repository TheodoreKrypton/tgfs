from typing import Tuple

from tgfs.errors import TechnicalError


def split_global_path(path: str) -> Tuple[str, str]:
    """
    Split a path into the client name and the sub path.
    Example:
        - Input: "notes-1/test/test.txt"
        - Output: ("notes-1", "test/test.txt")
    """
    if not path.startswith("/"):
        path = f"/{path}"
    parts = path.split("/", 2)
    if len(parts) < 3:
        raise TechnicalError(
            f"Path must contain a client name and may contain a sub path. Got: {path}"
        )
    return parts[1], parts[2]
