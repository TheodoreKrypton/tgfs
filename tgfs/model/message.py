from typing import TypedDict, Literal


class TGFSFileVersionSerialized(TypedDict):
    type: Literal["FV"]
    id: str
    updated_at: int
    message_id: int
    size: int


class TGFSFileObject(TypedDict):
    type: Literal["F"]
    name: str
    versions: list[TGFSFileVersionSerialized]


class TGFSFileRefSerialized(TypedDict):
    type: Literal["FR"]
    messageId: int
    name: str


class TGFSDirectorySerialized(TypedDict):
    type: Literal["D"]
    name: str
    children: list["TGFSDirectorySerialized"]
    files: list[TGFSFileRefSerialized]
