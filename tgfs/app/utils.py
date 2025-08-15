from typing import Tuple

from tgfs.errors import TechnicalError


def split_global_path(path: str) -> Tuple[str, str]:
    """
    Split a path into the client name and the sub path.
    Example:
        - Input: "notes-1/test/test.txt"
        - Output: ("notes-1", "test/test.txt")
    """
    if not path[0] == "/":
        path = f"/{path}"
    parts = path.split("/", 2)
    if len(parts) < 1:
        raise TechnicalError(f"Path must begin with a client name. Got: {path}")
    if len(parts) == 2:
        return parts[1], ""
    return parts[1], parts[2]
