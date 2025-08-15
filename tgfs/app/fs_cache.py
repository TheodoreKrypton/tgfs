from collections import defaultdict
from typing import Dict, List, Optional

from asgidav.member import Member

MaybeMember = Optional[Member]


class FSCache:
    def __init__(self, value: MaybeMember = None):
        self._cache: Dict[str, FSCache] = defaultdict(FSCache)
        self._value: MaybeMember = value

    @staticmethod
    def split_path(path: str) -> List[str]:
        path = path.strip("/")
        if path == "":
            return [""]
        return ["", *path.split("/")]

    def __get(self, parts: List[str]) -> "FSCache":
        if not parts:
            return self
        return self._cache[parts[0]].__get(parts[1:])

    def get(self, parts: str) -> MaybeMember:
        return self.__get(self.split_path(parts))._value

    def __set(self, path: List[str], value: MaybeMember):
        if len(path) == 1:
            self._cache[path[0]] = FSCache(value)
        else:
            self._cache[path[0]].__set(path[1:], value)

    def set(self, path: str, value: MaybeMember):
        self.__set(self.split_path(path), value)

    def reset(self, path: str):
        parts = self.split_path(path)
        self.__set(parts, None)

    def reset_parent(self, path: str):
        parts = self.split_path(path)
        self.__set(parts[:-1], None)


gfc: Dict[str, FSCache] = {}
