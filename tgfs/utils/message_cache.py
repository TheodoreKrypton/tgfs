from typing import Generic, TypeVar, Optional, Iterable, List, Tuple

from lru import LRU  # type: ignore

from tgfs.reqres import MessageResp

K = TypeVar("K")
V = TypeVar("V")


class MessageCache(Generic[K, V]):
    def __init__(self):
        self._lru = LRU(1024)  # type: LRU[K, V]

    def get(self, key: K) -> Optional[V]:
        return self._lru.get(key)

    def __setitem__(self, key: K, value: V) -> None:
        self._lru[key] = value

    def __getitem__(self, key: K) -> V:
        return self._lru[key]

    def __contains__(self, key: K) -> bool:
        return key in self._lru

    def gets(self, keys: Iterable[K]) -> List[Optional[V]]:
        return [self.get(key) for key in keys]

    def find_nonexistent(self, keys: Iterable[K]) -> List[K]:
        return [key for key in keys if self.get(key) is None]


message_cache_by_id = MessageCache[int, Optional[MessageResp]]()
message_cache_by_search = MessageCache[str, Tuple[MessageResp, ...]]()
