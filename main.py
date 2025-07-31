import asyncio
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from tgfs.app import create_manager_app, create_webdav_app
from tgfs.config import Config, get_config
from tgfs.core import Client
from tgfs.telegram import login_as_account, login_as_bots


async def create_client(config: Config):
    account = await login_as_account(config)
    bots = await login_as_bots(config)

    return await Client.create(account, bots)


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
    logger = logging.getLogger(__name__)

    client = await create_client(config)

    # Create WebDAV app
    webdav_app = create_webdav_app(client, config)

    # Start WebDAV server
    webdav_task = asyncio.create_task(
        run_server(webdav_app, config.webdav.host, config.webdav.port, "WebDAV")
    )

    # Start manager server if configured
    tasks = [webdav_task]
    if config.manager:
        manager_app = create_manager_app()
        manager_task = asyncio.create_task(
            run_server(manager_app, config.manager.host, config.manager.port, "Task Manager")
        )
        tasks.append(manager_task)
        logger.info(f"Task Manager server will start on {config.manager.host}:{config.manager.port}")
    else:
        logger.info("Task Manager not configured, skipping...")

    # Wait for all servers to complete
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
