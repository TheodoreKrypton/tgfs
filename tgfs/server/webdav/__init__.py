from asgidav.app import app, RootFolder
from .folder import Folder


def create_webdav_app(client):
    RootFolder.set(Folder("/", client))
    return app
