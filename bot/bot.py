import logging

from disnake.ext import commands

from bot import constants

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class SirRobin(commands.Bot):
    """Sir-Robin core."""

    def add_cog(self, cog: commands.Cog) -> None:
        """
        Delegate to super to register `cog`.

        This only serves to make the info log, so that extensions don't have to.
        """
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")


bot = SirRobin(command_prefix=constants.Client.prefix)
