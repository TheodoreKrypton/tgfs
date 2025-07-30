from typing import Literal, TypedDict, List


class TGFSFileVersionSerialized(TypedDict):
    type: Literal["FV"]
    id: str
    updatedAt: int
    messageId: int
    messageIds: List[int]
    size: int


class TGFSFileDescSerialized(TypedDict):
    type: Literal["F"]
    name: str
    versions: List[TGFSFileVersionSerialized]


class TGFSFileRefSerialized(TypedDict):
    type: Literal["FR"]
    messageId: int
    name: str


class TGFSDirectorySerialized(TypedDict):
    type: Literal["D"]
    name: str
    children: List["TGFSDirectorySerialized"]
    files: List[TGFSFileRefSerialized]
