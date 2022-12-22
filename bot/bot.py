import asyncio

import discord
from discord.ext import commands
from pydis_core import BotBase
from pydis_core.site_api import APIClient
from pydis_core.utils import scheduling
from pydis_core.utils.logging import get_logger
from pydis_core.utils.scheduling import create_task

from bot import constants, exts
from bot.exts.code_jams._views import JamTeamInfoView

log = get_logger(__name__)


class SirRobin(BotBase):
    """Sir-Robin core."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cog_load_task: asyncio.Task | None = None
        self.code_jam_mgmt_api: APIClient | None = None

    async def close(self) -> None:
        """On close, cleanly close the aiohttp client session."""
        await super().close()
        await self.code_jam_mgmt_api.close()

    async def setup_hook(self) -> None:
        """Default Async initialisation method for Discord.py."""
        self.code_jam_mgmt_api = APIClient(
            site_api_url=constants.Client.code_jam_api,
            site_api_token=constants.Client.code_jam_token
        )
        await super().setup_hook()
        self.cog_load_task = scheduling.create_task(self.load_extensions(exts))
        scheduling.create_task(self.reload_commands())
        create_task(self.check_channels())
        create_task(self.send_log(constants.Client.name, "Connected!"))
        self.add_view(JamTeamInfoView(self))

    async def reload_commands(self) -> None:
        """Sync all application commands after loading cogs."""
        await self.cog_load_task
        await self.tree.sync(guild=discord.Object(self.guild_id))

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

    async def invoke_help_command(self, ctx: commands.Context) -> None:
        """Invoke the help command or default help command if help extensions is not loaded."""
        if "bot.exts.core.help" in ctx.bot.extensions:
            help_command = ctx.bot.get_command("help")
            await ctx.invoke(help_command, ctx.command.qualified_name)
            return
        await ctx.send_help(ctx.command)
