from typing import Iterable, Optional, TypeVar

T = TypeVar("T")


def exclude_none(iterable: Iterable[Optional[T]]) -> Iterable[T]:
    return (item for item in iterable if item is not None)
