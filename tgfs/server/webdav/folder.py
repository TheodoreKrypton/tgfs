import time
from typing import Optional

from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
from wsgidav.dav_provider import DAVCollection

from .resource import Resource

class Folder(DAVCollection):
    def __init__(self, path: str, environ):
        super().__init__(path, environ)
        self.items = {}
        self.created =  time.time()
        self.modified = self.created

    def get_creation_date(self) -> Optional[float]:
        return self.created

    def get_last_modified(self):
        return self.modified

    def get_display_name(self) -> str:
        return self.name

    def get_member_names(self):
        return list(self.items.keys())

    def get_member(self, name):
        return self.items.get(name)

    def _sub_path(self, name: str):
        if self.path.endswith("/"):
            return f"{self.path}{name}"
        else:
            return f"{self.path}/{name}"

    def create_empty_resource(self, name: str):
        assert name not in self.items, f"Resource {name} already exists"
        path = self._sub_path(name)
        resource = Resource(str(path), self.environ)
        self.items[name] = resource
        self.modified = time.time()
        return resource

    def create_collection(self, name: str):
        assert name not in self.items, f"Folder {name} already exists"
        path = self._sub_path(name)
        folder = Folder(path, self.environ)
        self.items[name] = folder
        self.modified = time.time()
        return folder

    def support_recursive_delete(self):
        return True

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN)

    def get_ref_url(self):
        return self.path
