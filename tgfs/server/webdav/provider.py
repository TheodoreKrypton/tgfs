from wsgidav.dav_provider import DAVProvider

from tgfs.server.webdav.folder import Folder


class Provider(DAVProvider):
    def __init__(self):
        super().__init__()
        self.root = Folder("/", {"wsgidav.provider": self})

        docs = self.root.create_collection("documents")
        readme = docs.create_empty_resource("readme.txt")
        readme.content = b"This is a readme file."

        notes = docs.create_collection("notes")
        note = notes.create_empty_resource("note.txt")
        note.content = b"This is a note file."

    def get_resource_inst(self, path: str, environ: dict):
        parts = path.strip("/").split("/")
        current = self.root
        current.environ = environ

        if path == "/" or path == "":
            return current

        for i, part in enumerate(parts):
            if not part:
                continue

            next_resource = current.get_member(part)
            if next_resource is None:
                return None

            next_resource.environ = environ
            current = next_resource

        return current
