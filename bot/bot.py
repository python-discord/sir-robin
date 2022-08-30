import discord
from botcore import BotBase
from botcore.site_api import APIClient
from botcore.utils.logging import get_logger
from botcore.utils.scheduling import create_task

from bot import constants, exts
from bot.exts.code_jams._views import JamTeamInfoView

log = get_logger(__name__)


class SirRobin(BotBase):
    """Sir-Robin core."""

    async def close(self) -> None:
        """On close, cleanly close the aiohttp client session."""
        await super().close()
        await self.code_jam_mgmt_api.close()

    async def setup_hook(self) -> None:
        """Default Async initialisation method for Discord.py."""
        await super().setup_hook()

        create_task(self.load_extensions(exts))
        create_task(self.check_channels())
        create_task(self.send_log(constants.Client.name, "Connected!"))
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
        """Setup a Code Jam Management APIClient."""
        self.code_jam_mgmt_api = APIClient(
            site_api_url=constants.Client.code_jam_api,
            site_api_token=constants.Client.code_jam_token
        )
        await super().login(*args, **kwargs)
