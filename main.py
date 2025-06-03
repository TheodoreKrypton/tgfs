import asyncio

from telethon.tl.types import PeerChat, PeerChannel

from tgfs.config import get_config, set_config_file
from tgfs.api.impl.telethon import login_as_account, login_as_bot
from tgfs.api.client.api.client import Client


async def main():
    set_config_file(f"config.yaml")

    config = get_config()
    account = await login_as_account(config)

    bot = await login_as_bot(config)

    client = await Client.create(account, bot)


if __name__ == "__main__":
    asyncio.run(main())
