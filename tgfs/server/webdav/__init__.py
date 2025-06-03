from wsgidav.wsgidav_app import WsgiDAVApp

from tgfs.server.webdav.provider import Provider


def create_webdav_app(client):
    server_config = {
        "provider_mapping": {
            "/": Provider(client),
        },
        "verbose": 2,
        "logging.enable_loggers": [],
        "property_manager": True,
        "lock_storage": True,
        "http_authenticator": {
            "domain_controller": None,
            "accept_basic": True,
            "accept_digest": True,
            "default_to_digest": True,
            "trusted_auth_header": None,
        },
        "simple_dc": {
            "user_mapping": {
                "*": {
                    "user0": {
                        "password": "password0",
                    }
                }
            },
        },
    }

    return WsgiDAVApp(server_config)
