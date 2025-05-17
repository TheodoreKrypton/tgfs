from cheroot import wsgi
from wsgidav.wsgidav_app import WsgiDAVApp

from tgfs.server.webdav.provider import Provider


def get_config():
    return {
        "provider_mapping": {
            "/virtual": Provider(),
        },
        "verbose": 3,
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
                "*": True
            },
        },
    }


if __name__ == "__main__":
    config = get_config()
    app = WsgiDAVApp(config)
    server = wsgi.Server(
        bind_addr=("0.0.0.0", 8080),
        wsgi_app=app,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("Server stopped by user.")
    finally:
        server.stop()
        print("Server stopped.")
