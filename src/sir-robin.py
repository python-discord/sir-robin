import os
from pathlib import Path

import disnake
from dotenv import load_dotenv
from loguru import logger
from disnake.ext import commands

from util.constants import walk_extensions

path = Path(__file__)
parent = path.parents[1]
load_dotenv(parent.joinpath(".env"))
DEV_LOG = os.environ.get("DEV_LOG")
TOKEN = os.environ.get("TOKEN")


class SirRobin(commands.Bot):
    """
    Bradbot core.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "Bradbot"
        self.dev_log = int(DEV_LOG)

    def add_cog(self, cog: commands.Cog) -> None:
        """
        Delegate to super to register `cog`.
        This only serves to make the info log, so that extensions don't have to.
        """
        super().add_cog(cog)
        logger.info(f"Cog loaded: {cog.qualified_name}")


bot = SirRobin(command_prefix="&", DEV_LOG=DEV_LOG)


@bot.event
async def on_ready():
    logger.info("'on_ready' event hit")
    devlog = bot.get_channel(bot.dev_log)  # noqa: F841
    icon = bot.user.display_avatar.url

    embed = disnake.Embed(title="Sir Robin", description="Sir Robin online")
    embed.set_author(name=bot.name, icon_url=icon)
    await devlog.send(embed=embed)


for ext in walk_extensions():
    try:
        bot.load_extension(ext)
    except commands.errors.NoEntryPointError:
        pass


bot.run(TOKEN)
