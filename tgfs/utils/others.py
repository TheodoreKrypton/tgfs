from typing import Any, Iterable


def remove_none(iterable: Iterable[Any]) -> Iterable[Any]:
    return (item for item in iterable if item is not None)
