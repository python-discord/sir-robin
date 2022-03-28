import asyncio
import socket

import aiohttp

from bot.bot import bot
from bot.constants import Client

if not Client.in_ci:
    async def main() -> None:
        bot._resolver = aiohttp.AsyncResolver()

        # Use AF_INET as its socket family to prevent HTTPS related problems both locally
        # and in production.
        bot._connector = aiohttp.TCPConnector(
            resolver=bot._resolver,
            family=socket.AF_INET,
        )

        # Client.login() will call HTTPClient.static_login() which will create a session using
        # this connector attribute.
        bot.http.connector = bot._connector

        bot.http_session = aiohttp.ClientSession(connector=bot._connector)
        """Entry Async method for starting the bot."""
        async with bot:
            bot._guild_available = asyncio.Event()
            await bot.start(Client.token)

    asyncio.run(main())
