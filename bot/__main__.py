import asyncio

import discord
from async_rediscache import RedisSession

import bot
from bot import constants
from bot.bot import SirRobin
from bot.constants import Client

if not Client.in_ci:
    async def main() -> None:
        """Entry Async method for starting the bot."""
        # Default is all intents except for privileged ones (Members, Presences, ...)
        _intents = discord.Intents.default()
        _intents.bans = False
        _intents.integrations = False
        _intents.invites = False
        _intents.typing = False
        _intents.webhooks = False
        _intents.message_content = True
        _intents.members = True

        redis_session = RedisSession(
            address=(constants.RedisConfig.host, constants.RedisConfig.port),
            password=constants.RedisConfig.password,
            minsize=1,
            maxsize=20,
            use_fakeredis=constants.RedisConfig.use_fakeredis,
            global_namespace="sir-robin"
        )

        await redis_session.connect()

        bot.instance = SirRobin(
            redis_session=redis_session,
            command_prefix=constants.Client.prefix,
            activity=discord.Game("The Not-Quite-So-Bot-as-Sir-Lancebot"),
            intents=_intents,
        )
        async with bot.instance:
            bot.instance._guild_available = asyncio.Event()
            await bot.instance.start(Client.token)

    asyncio.run(main())
