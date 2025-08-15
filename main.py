import asyncio
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from tgfs.app import create_app
from tgfs.config import Config, get_config
from tgfs.core import Client, Clients
from tgfs.telegram import login_as_account, login_as_bots


async def create_clients(config: Config) -> Clients:
    account = await login_as_account(config) if config.telegram.account else None
    bots = await login_as_bots(config)

    clients: Clients = {}

    for channel_id in config.telegram.private_file_channel:
        metadata_cfg = config.tgfs.metadata[channel_id]
        clients[metadata_cfg.name] = await Client.create(
            channel_id,
            metadata_cfg,
            bots,
            account,
        )
    return clients


async def run_server(app, host: str, port: int, name: str):
    """Run a server with proper configuration"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {name} server on {host}:{port}")

    server_config = UvicornConfig(
        app,
        host=host,
        port=port,
        loop="none",
        log_level="info",
    )
    server = Server(config=server_config)
    await server.serve()


async def main():
    config = get_config()

    clients = await create_clients(config)

    app = create_app(clients, config)
    await run_server(app, config.tgfs.server.host, config.tgfs.server.port, "TGFS")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
