from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Self, Tuple

from tgfs.errors import FileOrDirectoryAlreadyExists, FileOrDirectoryDoesNotExist
from tgfs.utils.time import FIRST_DAY_OF_EPOCH, ts

from .common import validate_name
from .serialized import TGFSDirectorySerialized

# A cached name index: (number of entries, last entry seen, name -> positions).
# The length and the last entry act as an O(1) fingerprint of the entry list,
# so the index can also be invalidated by callers that mutate `files` /
# `children` directly instead of going through the helpers below.  Keeping a
# strong reference to the last entry also stops CPython from recycling its
# `id()` into a replacement entry.
NameIndex = Tuple[int, Optional[object], Dict[str, List[int]]]


@dataclass
class TGFSFileRef:
    message_id: int
    name: str
    location: "TGFSDirectory" = field(repr=False)

    def to_dict(self) -> dict:
        return dict(
            type="FR",
            messageId=self.message_id,
            name=self.name,
        )

    def delete(self) -> None:
        self.location.delete_file_ref(self)


@dataclass
class TGFSDirectory:
    name: str
    parent: Optional["TGFSDirectory"]
    children: list["TGFSDirectory"] = field(default_factory=list)
    files: list[TGFSFileRef] = field(default_factory=list)

    # Built lazily on the first lookup by name and dropped again whenever this
    # directory mutates its own entry lists.  Resolving a child by name is the
    # hot path (a WebDAV listing resolves every child one at a time), and
    # scanning the whole entry list per lookup costs O(N^2) for a directory
    # with N children.
    _files_by_name: Optional[NameIndex] = field(
        default=None, init=False, repr=False, compare=False
    )
    _children_by_name: Optional[NameIndex] = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self):
        validate_name(self.name)

    # ------------------------------------------------------------------
    # name index management
    # ------------------------------------------------------------------

    @staticmethod
    def _index_is_fresh(cached: NameIndex, entries: list) -> bool:
        """O(1) check that `cached` still describes `entries`."""
        length, last, _ = cached
        return length == len(entries) and last is (entries[-1] if entries else None)

    def _build_index(self, entries: list) -> NameIndex:
        index: Dict[str, List[int]] = {}
        for position, entry in enumerate(entries):
            bucket = index.get(entry.name)
            if bucket is None:
                index[entry.name] = [position]
            else:
                bucket.append(position)
        return (len(entries), entries[-1] if entries else None, index)

    def _files_index(self) -> Dict[str, List[int]]:
        cached = self._files_by_name
        if cached is None or not self._index_is_fresh(cached, self.files):
            cached = self._build_index(self.files)
            self._files_by_name = cached
        return cached[2]

    def _children_index(self) -> Dict[str, List[int]]:
        cached = self._children_by_name
        if cached is None or not self._index_is_fresh(cached, self.children):
            cached = self._build_index(self.children)
            self._children_by_name = cached
        return cached[2]

    def _invalidate_files_index(self) -> None:
        self._files_by_name = None

    def _invalidate_children_index(self) -> None:
        self._children_by_name = None

    @staticmethod
    def _collect(entries: list, index: Dict[str, List[int]], names: Iterable[str]):
        """Entries matching `names`, in directory order, query names deduped."""
        positions: List[int] = []
        for name in dict.fromkeys(names):
            bucket = index.get(name)
            if bucket:
                positions.extend(bucket)
        if not positions:
            return []
        positions.sort()
        return [entries[position] for position in positions]

    # ------------------------------------------------------------------
    # (de)serialization
    # ------------------------------------------------------------------

    @property
    def created_at_timestamp(self) -> int:
        return ts(FIRST_DAY_OF_EPOCH)

    def to_dict(self) -> dict:
        return dict(
            type="D",
            name=self.name,
            children=[child.to_dict() for child in self.children],
            files=[file.to_dict() for file in self.files],
        )

    @staticmethod
    def from_dict(
        data: TGFSDirectorySerialized, parent: Optional["TGFSDirectory"] = None
    ) -> "TGFSDirectory":
        d = TGFSDirectory(
            name=data["name"],
            parent=parent,
            children=[],
            files=[],
        )

        if data["files"]:
            d.files = [
                TGFSFileRef(message_id=file["messageId"], name=file["name"], location=d)
                for file in data["files"]
                if file["name"] and file["messageId"]
            ]

        d.children = [TGFSDirectory.from_dict(child, d) for child in data["children"]]
        return d

    # ------------------------------------------------------------------
    # mutation
    # ------------------------------------------------------------------

    def create_dir(
        self, name: str, dir_to_copy: Optional["TGFSDirectory"]
    ) -> "TGFSDirectory":
        if len(self.find_dirs([name])) > 0:
            raise FileOrDirectoryAlreadyExists(name)

        child = TGFSDirectory(
            name=name,
            parent=self,
            children=[] if not dir_to_copy else dir_to_copy.children,
            files=[] if not dir_to_copy else dir_to_copy.files,
        )

        self.children.append(child)
        self._invalidate_children_index()
        return child

    def create_file_ref(self, name: str, fd_message_id: int) -> TGFSFileRef:
        if self.find_files([name]):
            raise FileOrDirectoryAlreadyExists(name)

        fr = TGFSFileRef(
            message_id=fd_message_id,
            name=name,
            location=self,
        )
        self.files.append(fr)
        self._invalidate_files_index()
        return fr

    def delete_file_ref(self, fr: TGFSFileRef) -> None:
        self.files.remove(fr)
        self._invalidate_files_index()

    def delete(self) -> None:
        if self.parent:
            self.parent.children.remove(self)
            self.parent._invalidate_children_index()
        else:
            # root directory, just clear its contents
            self.children.clear()
            self.files.clear()
            self._invalidate_children_index()
            self._invalidate_files_index()

    # ------------------------------------------------------------------
    # lookup
    # ------------------------------------------------------------------

    @classmethod
    def root_dir(cls) -> Self:
        return cls(name="root", parent=None)

    def find_dirs(self, names: Iterable[str] = tuple()) -> List["TGFSDirectory"]:
        if not names:
            return self.children
        return self._collect(self.children, self._children_index(), names)

    def find_dir(self, name: str) -> "TGFSDirectory":
        dirs = self.find_dirs([name])
        if not dirs:
            raise FileOrDirectoryDoesNotExist(name)
        return dirs[0]

    def find_files(self, names: Iterable[str] = tuple()) -> List[TGFSFileRef]:
        if not names:
            return self.files
        return self._collect(self.files, self._files_index(), names)

    def find_file(self, name: str) -> TGFSFileRef:
        files = self.find_files([name])
        if not files:
            raise FileOrDirectoryDoesNotExist(name)
        return files[0]

    @property
    def absolute_path(self) -> str:
        if self.parent is None:
            return ""
        return (
            f"{self.parent.absolute_path}/{self.name}"
            if self.name
            else self.parent.absolute_path
        )
