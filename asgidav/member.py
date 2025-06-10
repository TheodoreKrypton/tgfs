from abc import ABC, abstractmethod
from typing import TypedDict
import datetime
import email
from email.utils import formatdate
from enum import Enum


class ResourceType(Enum):
    DEFAULT = ""
    COLLECTION = "<D:collection/>"


class Properties(TypedDict, total=False):
    getlastmodified: str
    creationdate: str
    displayname: str
    resourcetype: str
    getcontenttype: str


class Member(ABC):
    resource_type: ResourceType = ResourceType.DEFAULT

    def __init__(self, path: str):
        self.path = path
        self.is_hidden = False
        self.is_readonly = False
        self.is_root = False

    @abstractmethod
    async def content_type(self) -> str:
        pass

    @abstractmethod
    async def display_name(self) -> str:
        raise NotImplemented

    @abstractmethod
    async def creation_date(self) -> int:
        raise NotImplemented

    @abstractmethod
    async def last_modified(self) -> int:
        raise NotImplemented

    @abstractmethod
    async def get_properties(self) -> Properties:
        return Properties(
            getlastmodified=self.unixdate2iso8601(await self.last_modified()),
            creationdate=self.unixdate2iso8601(await self.creation_date()),
            displayname=await self.display_name(),
            resourcetype=self.resource_type.value,
            getcontenttype=await self.content_type(),
        )

    @classmethod
    def unixdate2iso8601(cls, t: float):
        print(t)
        return datetime.datetime.fromtimestamp(
            t / 1000, tz=datetime.timezone.utc
        ).isoformat()

    @classmethod
    def unixdate2rfc1123(cls, t: float):
        return email.utils.formatdate(t, usegmt=True)
