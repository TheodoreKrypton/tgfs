from asgidav.app import RootFolder, app

from .folder import Folder


def create_webdav_app(client):
    RootFolder.set_method(lambda: Folder("/", client))
    return app
