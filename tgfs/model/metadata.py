from dataclasses import dataclass

from .directory import TGFSDirectory


@dataclass
class TGFSMetadata:
    dir: TGFSDirectory
    message_id: int = -1

    @staticmethod
    def from_dict(data: dict) -> "TGFSMetadata":
        return TGFSMetadata(
            dir=TGFSDirectory.from_dict(data["dir"]),
        )

    def to_dict(self) -> dict:
        return {
            "type": "TGFSMetadata",
            "dir": self.dir.to_dict(),
        }
