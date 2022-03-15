import asyncio

from bot.bot import bot
from bot.constants import Client

if not Client.in_ci:
    async def main() -> None:
        """Entry Async method for starting the bot."""
        async with bot:
            bot._guild_available = asyncio.Event()
            await bot.start(Client.token)

    asyncio.run(main())
