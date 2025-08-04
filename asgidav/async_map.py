import asyncio
from typing import Any, Callable, Coroutine, Iterable, List, TypeVar

T = TypeVar("T")
U = TypeVar("U")


async def async_map(
    func: Callable[[T], Coroutine[Any, Any, U]], iterable: Iterable[T]
) -> List[U]:
    tasks: List[asyncio.Task[U]] = [
        asyncio.create_task(func(item)) for item in iterable
    ]
    return await asyncio.gather(*tasks)
