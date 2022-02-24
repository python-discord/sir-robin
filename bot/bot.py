import logging
import os

import disnake
from disnake.ext import commands

log = logging.getLogger(__name__)

try:
    import dotenv
    dotenv.load_dotenv()
except ModuleNotFoundError:
    pass

DEV_LOG_CHANNEL = os.environ.get("DEV_LOG_CHANNEL")
TOKEN = os.environ.get("TOKEN")


class SirRobin(commands.Bot):
    """Sir-Robin core."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "Sir-Robin"
        self.dev_log = int(DEV_LOG_CHANNEL)

    def add_cog(self, cog: commands.Cog) -> None:
        """Delegate to super to register `cog`.

        This only serves to make the info log, so that extensions don't have to.
        """
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")


bot = SirRobin(command_prefix="&", DEV_LOG=DEV_LOG_CHANNEL)


@bot.event
async def on_ready():
    log.info("'on_ready' event hit")
    devlog = bot.get_channel(bot.dev_log)  # noqa: F841
    icon = bot.user.display_avatar.url

    embed = disnake.Embed(title="Sir Robin", description="Sir Robin online")
    embed.set_author(name=bot.name, icon_url=icon)
    await devlog.send(embed=embed)
