import datetime
from uuid import uuid4 as uuid
from dataclasses import dataclass, field

from tgfs.api.types import SentFileMessage
from .message import TGFSFileVersionSerialized, TGFSFileObject

EMPTY_FILE = -1
INVALID_FILE_SIZE = -1


@dataclass
class TGFSFileVersion:
    id: str
    updated_at: datetime.datetime
    message_id: int
    size: int

    def to_dict(self) -> TGFSFileVersionSerialized:
        return TGFSFileVersionSerialized(
            type="FV",
            id=self.id,
            updated_at=int(self.updated_at.timestamp()),
            message_id=self.message_id,
            size=self.size,
        )

    @staticmethod
    def empty() -> "TGFSFileVersion":
        return TGFSFileVersion(
            id=str(uuid()),
            updated_at=datetime.datetime.now(),
            message_id=EMPTY_FILE,
            size=INVALID_FILE_SIZE,
        )

    @staticmethod
    def from_sent_file_message(message: SentFileMessage) -> "TGFSFileVersion":
        return TGFSFileVersion(
            id=str(uuid()),
            updated_at=datetime.datetime.now(),
            message_id=message.message_id,
            size=message.size,
        )

    @staticmethod
    def from_dict(data: TGFSFileVersionSerialized) -> "TGFSFileVersion":
        return TGFSFileVersion(
            id=data["id"],
            updated_at=datetime.datetime.fromtimestamp(data["updated_at"]),
            message_id=data["message_id"],
            size=data["size"] or INVALID_FILE_SIZE,
        )

    def set_invalid(self):
        self.message_id = EMPTY_FILE
        self.size = INVALID_FILE_SIZE


@dataclass
class TGFSFile:
    name: str
    latest_version_id: str = ""
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    versions: dict[str, TGFSFileVersion] = field(default_factory=dict)

    def to_dict(self) -> TGFSFileObject:
        return TGFSFileObject(
            type="F",
            name=self.name,
            versions=[v.to_dict() for v in self.get_versions(sort=True)],
        )

    @staticmethod
    def from_dict(data: TGFSFileObject) -> "TGFSFile":
        versions = {v["id"]: TGFSFileVersion.from_dict(v) for v in data["versions"]}
        latest_version_id = max(versions, key=lambda k: versions[k].updated_at)
        return TGFSFile(
            versions=versions,
            latest_version_id=latest_version_id,
            created_at=datetime.datetime.now(),
            name=data["name"],
        )

    @staticmethod
    def empty(name: str) -> "TGFSFile":
        return TGFSFile(
            versions={},
            latest_version_id="",
            created_at=datetime.datetime.now(),
            name=name,
        )

    def get_latest_version(self) -> TGFSFileVersion:
        return self.versions[self.latest_version_id]

    def get_version(self, version_id: str) -> TGFSFileVersion:
        return self.versions[version_id]

    def add_version(self, version: TGFSFileVersion) -> None:
        self.versions[version.id] = version
        if version.updated_at > self.versions[self.latest_version_id].updated_at:
            self.latest_version_id = version.id
        if not self.created_at or version.updated_at < self.created_at:
            self.created_at = version.updated_at

    def add_empty_version(self) -> None:
        version = TGFSFileVersion.empty()
        self.add_version(version)

    def add_version_from_sent_file_message(self, msg: SentFileMessage):
        version = TGFSFileVersion.from_sent_file_message(msg)
        self.add_version(version)
        return self.versions[self.latest_version_id]

    def update_version(self, version: TGFSFileVersion):
        self.versions[version.id] = version

    def get_versions(self, sort: bool = False, exclude_empty: bool = False):
        if not sort:
            res = self.versions.values()
        else:
            res = sorted(
                self.versions.values(),
                key=lambda v: v.updataed_at,
                reverse=True,
            )

        if exclude_empty:
            res = [
                v
                for v in res
                if v.message_id != EMPTY_FILE and v.size != INVALID_FILE_SIZE
            ]
        return res

    def delete_version(self, version_id: str) -> None:
        if version_id not in self.versions:
            raise ValueError(f"Version {version_id} not found in file {self.name}.")
        del self.versions[version_id]
        if version_id == self.latest_version_id:
            if self.versions:
                self.latest_version_id = max(
                    self.versions, key=lambda k: self.versions[k].updated_at
                )
            else:
                self.latest_version_id = ""
