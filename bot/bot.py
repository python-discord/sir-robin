import asyncio
import socket
from typing import Optional

import aiohttp
import discord
from botcore.site_api import APIClient
from botcore.utils.extensions import walk_extensions
from botcore.utils.logging import get_logger
from botcore.utils.scheduling import create_task
from discord.ext import commands

from bot import constants, exts
from bot.exts.code_jams._views import JamTeamInfoView

log = get_logger(__name__)


class SirRobin(commands.Bot):
    """Sir-Robin core."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # This session may want to be recreated on login/disconnect.
        # Additionally, on the bot repo we use a different connector that is more "stable".
        self.code_jam_mgmt_api: Optional[APIClient] = None
        self.http_session: Optional[aiohttp.ClientSession] = None

        self._guild_available: Optional[asyncio.Event] = None
        self.http_session: Optional[aiohttp.ClientSession] = None

    async def close(self) -> None:
        """On close, cleanly close the aiohttp client session."""
        await self.http_session.close()
        await self.code_jam_mgmt_api.close()
        await super().close()

    async def add_cog(self, cog: commands.Cog, **kwargs) -> None:
        """
        Delegate to super to register `cog`.

        This only serves to make the info log, so that extensions don't have to.
        """
        await super().add_cog(cog, **kwargs)
        log.info(f"Cog loaded: {cog.qualified_name}")

    async def load_all_extensions(self) -> None:
        """Loads all the extensions in the `exts` module."""
        for ext in walk_extensions(exts):
            await self.load_extension(ext)

    async def setup_hook(self) -> None:
        """Default Async initialisation method for Discord.py."""
        await super().setup_hook()
        create_task(self.load_all_extensions(), event_loop=self.loop)
        create_task(self.check_channels(), event_loop=self.loop)
        create_task(self.send_log(constants.Client.name, "Connected!"), event_loop=self.loop)
        self.add_view(JamTeamInfoView(self))

    async def check_channels(self) -> None:
        """Verifies that all channel constants refer to channels which exist."""
        await self.wait_until_guild_available()

        if constants.Client.debug:
            log.info("Skipping Channels Check.")
            return

        all_channels_ids = [channel.id for channel in self.get_all_channels()]
        for name, channel_id in vars(constants.Channels).items():
            if name.startswith("_"):
                continue
            if channel_id not in all_channels_ids:
                log.error(f'Channel "{name}" with ID {channel_id} missing')

    async def send_log(self, title: str, details: str = None, *, icon: str = None) -> None:
        """Send an embed message to the devlog channel."""
        await self.wait_until_guild_available()
        devlog = self.get_channel(constants.Channels.devlog)

        if not devlog:
            log.info(f"Fetching devlog channel as it wasn't found in the cache (ID: {constants.Channels.devlog})")
            try:
                devlog = await self.fetch_channel(constants.Channels.devlog)
            except discord.HTTPException as discord_exc:
                log.exception("Fetch failed", exc_info=discord_exc)
                return

        if not icon:
            icon = self.user.display_avatar.url

        embed = discord.Embed(description=details)
        embed.set_author(name=title, icon_url=icon)

        await devlog.send(embed=embed)

    async def on_guild_available(self, guild: discord.Guild) -> None:
        """
        Set the internal `_guild_available` event when PyDis guild becomes available.

        If the cache appears to still be empty (no members, no channels, or no roles), the event
        will not be set.
        """
        if guild.id != constants.Client.guild:
            return

        if not guild.roles or not guild.members or not guild.channels:
            log.warning("Guild available event was dispatched but the cache appears to still be empty!")
            return

        self._guild_available.set()

    async def on_guild_unavailable(self, guild: discord.Guild) -> None:
        """Clear the internal `_guild_available` event when PyDis guild becomes unavailable."""
        if guild.id != constants.Client.guild:
            return

        self._guild_available.clear()

    async def wait_until_guild_available(self) -> None:
        """
        Wait until the PyDis guild becomes available (and the cache is ready).

        The on_ready event is inadequate because it only waits 2 seconds for a GUILD_CREATE
        gateway event before giving up and thus not populating the cache for unavailable guilds.
        """
        await self._guild_available.wait()

    async def login(self, *args, **kwargs) -> None:
        """Re-create the connector and set up sessions before logging into Discord."""
        # Use asyncio for DNS resolution instead of threads so threads aren't spammed.
        self._resolver = aiohttp.AsyncResolver()

        # Use AF_INET as its socket family to prevent HTTPS related problems both locally
        # and in production.
        self._connector = aiohttp.TCPConnector(
            resolver=self._resolver,
            family=socket.AF_INET,
        )

        # Client.login() will call HTTPClient.static_login() which will create a session using
        # this connector attribute.
        self.http.connector = self._connector

        self.http_session = aiohttp.ClientSession(connector=self._connector)
        self.code_jam_mgmt_api = APIClient(
            site_api_url=constants.Client.code_jam_api,
            site_api_token=constants.Client.code_jam_token
        )
        await super().login(*args, **kwargs)


_intents = discord.Intents.default()  # Default is all intents except for privileged ones (Members, Presences, ...)
_intents.bans = False
_intents.integrations = False
_intents.invites = False
_intents.typing = False
_intents.webhooks = False
_intents.message_content = True
_intents.members = True

bot = SirRobin(
    command_prefix=constants.Client.prefix,
    activity=discord.Game("The Not-Quite-So-Bot-as-Sir-Lancebot"),
    intents=_intents,
)
