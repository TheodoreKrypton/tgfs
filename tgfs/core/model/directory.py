from dataclasses import dataclass, field
from typing import Iterable, Optional

from tgfs.errors import FileOrDirectoryAlreadyExists, FileOrDirectoryDoesNotExist

from .common import FIRST_DAY_OF_EPOCH, ts, validate_name
from .serialized import TGFSDirectorySerialized


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

    def __post_init__(self):
        validate_name(self.name)

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
        return child

    @classmethod
    def root_dir(cls) -> "TGFSDirectory":
        return cls(name="root", parent=None)

    def find_dirs(self, names: Iterable[str] = tuple()) -> list["TGFSDirectory"]:
        if not names:
            return self.children
        return [child for child in self.children if child.name in frozenset(names)]

    def find_dir(self, name: str) -> "TGFSDirectory":
        dirs = self.find_dirs([name])
        if not dirs:
            raise FileOrDirectoryDoesNotExist(name)
        return dirs[0]

    def find_files(self, names: Iterable[str] = tuple()) -> list[TGFSFileRef]:
        if not names:
            return self.files
        return [file for file in self.files if file.name in frozenset(names)]

    def find_file(self, name: str) -> TGFSFileRef:
        files = self.find_files([name])
        if not files:
            raise FileOrDirectoryDoesNotExist(name)
        return files[0]

    def create_file_ref(self, name: str, file_message_id: int) -> TGFSFileRef:
        if self.find_files([name]):
            raise FileOrDirectoryAlreadyExists(name)

        fr = TGFSFileRef(
            message_id=file_message_id,
            name=name,
            location=self,
        )
        self.files.append(fr)
        return fr

    def delete_file_ref(self, fr: TGFSFileRef) -> None:
        self.files.remove(fr)

    def delete(self) -> None:
        if self.parent:
            self.parent.children.remove(self)
        else:
            # root directory, just clear its contents
            self.children.clear()
            self.files.clear()

    @property
    def absolute_path(self) -> str:
        if self.parent is None:
            return f"/{self.name}"
        return (
            f"{self.parent.absolute_path}/{self.name}"
            if self.name
            else self.parent.absolute_path
        )
