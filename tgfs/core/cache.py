from typing import Optional, Dict, List, Union
from collections import defaultdict

from tgfs.core.model import TGFSDirectory, TGFSFileRef


CacheItem = Union[TGFSFileRef, TGFSDirectory]


class FSCache:
    def __init__(self, value: Optional[CacheItem] = None):
        self._cache: Dict[str, FSCache] = defaultdict(FSCache)
        self._value: Optional[CacheItem] = value

    @staticmethod
    def split_path(path: str) -> List[str]:
        path = path.strip("/")
        if path == "":
            return [""]
        return ["", *path.split("/")]

    def __get(self, path_parts: List[str]) -> "FSCache":
        if not path_parts:
            return self
        return self._cache[path_parts[0]].__get(path_parts[1:])

    def get(self, path: str) -> Optional[CacheItem]:
        return self.__get(self.split_path(path))._value

    def __set(self, path_parts: List[str], value: Optional[CacheItem]):
        if len(path_parts) == 1:
            self._cache[path_parts[0]] = FSCache(value)
        else:
            self._cache[path_parts[0]].__set(path_parts[1:], value)

    def set(self, path: str, value: Optional[CacheItem]):
        self.__set(self.split_path(path), value)

    def reset(self, path: str):
        parts = self.split_path(path)
        self.__set(parts, None)

    def reset_parent(self, path: str):
        parts = self.split_path(path)
        self.__set(parts[:-1], None)
