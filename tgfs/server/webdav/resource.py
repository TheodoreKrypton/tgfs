import io
import time
from typing import Optional

from wsgidav.dav_provider import DAVNonCollection


class Resource(DAVNonCollection):
    def __init__(self, path, environ, content=b""):
        super().__init__(path, environ)
        self.content = content
        self.created = time.time()
        self.modified = self.created

    def get_content_length(self):
        return len(self.content)

    def get_content_type(self):
        return "text/plain"

    def get_creation_date(self) -> Optional[float]:
        return self.created

    def get_last_modified(self):
        return self.modified

    def get_display_name(self) -> str:
        return self.name

    def get_content(self):
        return io.BytesIO(self.content)

    def support_etag(self):
        return True

    def get_etag(self):
        return f'"{hex(hash(self.content))}'[2:]

    def support_ranges(self):
        return False

    def begin_write(self, *, content_type=None):
        class WriteContext:
            def __init__(self, resource):
                self.resource = resource
                self.buffer = []

            def write(self, data):
                self.buffer.append(data)

            def close(self):
                self.resource.content = b"".join(self.buffer)
                self.resource.modified = time.time()
        return WriteContext(self)
