from botcore.utils.logging import get_logger

import disnake
from disnake.ext import commands

from bot import constants

log = get_logger(__name__)


class SirRobin(commands.Bot):
    """Sir-Robin core."""

    def add_cog(self, cog: commands.Cog) -> None:
        """
        Delegate to super to register `cog`.

        This only serves to make the info log, so that extensions don't have to.
        """
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")


bot = SirRobin(command_prefix=constants.Client.prefix, activity=disnake.Game("The Not-Quite-So-Bot-as-Sir-Lancebot"))
