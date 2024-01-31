import contextlib
from sys import exception

import discord
from discord.ext import commands
from pydis_core import BotBase
from pydis_core.site_api import APIClient
from pydis_core.utils.error_handling import handle_forbidden_from_block
from pydis_core.utils.logging import get_logger
from pydis_core.utils.scheduling import create_task
from sentry_sdk import push_scope

from bot import constants, exts
from bot.exts.code_jams._views import JamTeamInfoView

log = get_logger(__name__)


class SirRobin(BotBase):
    """Sir-Robin core."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.code_jam_mgmt_api: APIClient | None = None

    async def close(self) -> None:
        """On close, cleanly close the aiohttp client session."""
        await super().close()
        await self.code_jam_mgmt_api.close()

    async def setup_hook(self) -> None:
        """Default Async initialisation method for Discord.py."""
        self.code_jam_mgmt_api = APIClient(
            site_api_url=constants.Codejam.api,
            site_api_token=constants.Codejam.api_key
        )
        await super().setup_hook()
        await self.load_extensions(exts)
        create_task(self.check_channels())
        create_task(self.send_log(constants.Bot.name, "Connected!"))
        self.add_view(JamTeamInfoView(self))

    async def check_channels(self) -> None:
        """Verifies that all channel constants refer to channels which exist."""
        await self.wait_until_guild_available()

        if constants.Bot.debug:
            log.info("Skipping Channels Check.")
            return

        all_channels_ids = [channel.id for channel in self.get_all_channels()]
        for name, channel_id in vars(constants.Channels).items():
            if name.startswith("_"):
                continue
            if channel_id not in all_channels_ids:
                log.error(f'Channel "{name}" with ID {channel_id} missing')

    async def send_log(self, title: str, details: str | None = None, *, icon: str | None = None) -> None:
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

    async def on_error(self, event: str, *args, **kwargs) -> None:
        """Log errors raised in event listeners rather than printing them to stderr."""
        e_val = exception()

        if isinstance(e_val, discord.errors.Forbidden):
            message = args[0] if event == "on_message" else args[1] if event == "on_message_edit" else None

            with contextlib.suppress(discord.errors.Forbidden):
                # Attempt to handle the error. This re-raises the error if's not due to a block,
                # in which case the error is suppressed and handled normally. Otherwise, it was
                # handled so return.
                await handle_forbidden_from_block(e_val, message)
                return

        self.stats.incr(f"errors.event.{event}")

        with push_scope() as scope:
            scope.set_tag("event", event)
            scope.set_extra("args", args)
            scope.set_extra("kwargs", kwargs)

            log.exception(f"Unhandled exception in {event}.")
