from typing import Iterable, Optional, TypeVar

T = TypeVar("T")


def exclude_none(iterable: Iterable[Optional[T]]) -> Iterable[T]:
    return (item for item in iterable if item is not None)


def is_big_file(size: int) -> bool:
    return size > 10 * 1024 * 1024  # 10 MB
