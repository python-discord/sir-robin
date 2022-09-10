import asyncio

import aiohttp
import discord
from async_rediscache import RedisSession
from botcore import StartupError
from botcore.utils.logging import get_logger
from redis import RedisError

import bot
from bot import constants
from bot.bot import SirRobin

log = get_logger(__name__)


async def _create_redis_session() -> RedisSession:
    """Create and connect to a redis session."""
    redis_session = RedisSession(
        host=constants.RedisConfig.host,
        port=constants.RedisConfig.port,
        password=constants.RedisConfig.password,
        max_connections=20,
        use_fakeredis=constants.RedisConfig.use_fakeredis,
        global_namespace="bot",
        decode_responses=True,
    )
    try:
        return await redis_session.connect()
    except RedisError as e:
        raise StartupError(e)


if not constants.Client.in_ci:
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

        allowed_roles = (
            constants.Roles.events_lead,
            constants.Roles.code_jam_event_team,
            constants.Roles.code_jam_participants
        )
        async with aiohttp.ClientSession() as session:
            bot.instance = SirRobin(
                redis_session=await _create_redis_session(),
                http_session=session,
                guild_id=constants.Client.guild,
                allowed_roles=allowed_roles,
                command_prefix=constants.Client.prefix,
                activity=discord.Game("The Not-Quite-So-Bot-as-Sir-Lancebot"),
                intents=_intents,
            )
            async with bot.instance:
                await bot.instance.start(constants.Client.token)

    asyncio.run(main())
