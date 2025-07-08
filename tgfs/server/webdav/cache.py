from typing import Dict, Optional, Tuple

from asgidav.member import Member

MaybeMember = Optional[Member]


class FSCache:
    def __init__(self, value: MaybeMember = None):
        self._cache: Dict[str, Optional[FSCache]] = {}
        self._value: MaybeMember = value

    def get(self, path: str) -> Tuple[MaybeMember, "FSCache"]:
        path = path.strip("/")
        first_part, *rest = path.split("/", 1)
        if sub_folder := self._cache.get(first_part):
            if rest:
                return sub_folder.get(rest[0])
            return sub_folder._value, self
        return None, self

    def set(self, path: str, value: MaybeMember):
        path = path.strip("/")
        _, parent = self.get(path)
        last_part = path.split("/")[-1]
        parent._cache[last_part] = FSCache(value) if value else None

    def reset(self, path: str):
        self.set(path, None)


class RootCache:
    _cache = FSCache(None)

    @classmethod
    def get(cls, path: str) -> MaybeMember:
        res, _ = cls._cache.get(path)
        return res

    @classmethod
    def set(cls, path: str, value: MaybeMember):
        cls._cache.set(path, value)

    @classmethod
    def reset(cls, path: str):
        cls._cache.reset(path)
