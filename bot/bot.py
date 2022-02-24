import logging

import disnake
from disnake.ext import commands

from bot.constants import Channels

log = logging.getLogger(__name__)

try:
    import dotenv
    dotenv.load_dotenv()
except ModuleNotFoundError:
    pass


class SirRobin(commands.Bot):
    """Sir-Robin core."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "Sir-Robin"
        self.dev_log = Channels.devlog

    def add_cog(self, cog: commands.Cog) -> None:
        """
        Delegate to super to register `cog`.

        This only serves to make the info log, so that extensions don't have to.
        """
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")

    async def send_log(self, title: str, details: str = None, *, icon: str = None) -> None:
        """Send an embed message to the devlog channel."""
        await self.wait_until_guild_available()
        devlog = self.get_channel(Channels.devlog)

        if not devlog:
            log.info(f"Fetching devlog channel as it wasn't found in the cache (ID: {Channels.devlog})")
            try:
                devlog = await self.fetch_channel(Channels.devlog)
            except disnake.HTTPException as discord_exc:
                log.exception("Fetch failed", exc_info=discord_exc)
                return

        if not icon:
            icon = self.user.display_avatar.url

        embed = disnake.Embed(description=details)
        embed.set_author(name=title, icon_url=icon)

        await devlog.send(embed=embed)


bot = SirRobin(command_prefix="&", DEV_LOG=Channels.devlog)
