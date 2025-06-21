import asyncio

import uvicorn
from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from tgfs.api import Client, login_as_account, login_as_bot
from tgfs.config import Config, get_config, set_config_file
from tgfs.server.webdav import create_webdav_app


async def create_client(config: Config):
    account = await login_as_account(config)
    bot = await login_as_bot(config)

    return await Client.create(account, bot)


async def main():
    set_config_file("config.yaml")

    config = get_config()

    client = await create_client(config)

    app = create_webdav_app(client)

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
