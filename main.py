import asyncio
import logging

import uvicorn
from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from tgfs.telegram import login_as_account, login_as_bots
from tgfs.config import Config, get_config
from tgfs.core import Client
from tgfs.app import create_webdav_app

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def create_client(config: Config):
    account = await login_as_account(config)
    bots = await login_as_bots(config)

    return await Client.create(account, bots)


async def main():
    config = get_config()

    client = await create_client(config)

    app = create_webdav_app(client, config)

    server_config = UvicornConfig(
        app,
        host=config.webdav.host,
        port=config.webdav.port,
        loop="none",
    )
    server = Server(config=server_config)
    await server.serve()

    uvicorn.run(app, host=config.webdav.host, port=config.webdav.port)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
