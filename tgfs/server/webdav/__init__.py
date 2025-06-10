from asgidav.app import app, set_root_folder
from .folder import Folder


def create_webdav_app(client):
    set_root_folder(Folder("/", client))
    return app
