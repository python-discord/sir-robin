from discord import Colour, Embed
from discord.ext.commands import (BadArgument, Cog, CommandError,
                                  CommandNotFound, Context)

from bot.bot import SirRobin
from bot.log import get_logger

log = get_logger(__name__)


class ErrorHandler(Cog):
    """Handles errors emitted from commands."""

    def __init__(self, bot: SirRobin):
        self.bot = bot

    @staticmethod
    def _get_error_embed(title: str, body: str) -> Embed:
        """Return a embed with our error colour assigned."""
        return Embed(
            title=title,
            colour=Colour.brand_red(),
            description=body
        )

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError) -> None:
        """
        Generic command error handling from other cogs.

        Using the error type, handle the error appropriately.
            if there is no handling for the error type raised,
            a message will be sent to the user & it will be logged.

        In the future, I would expect this to be used as a place
            to push errors to a sentry instance.
        """
        log.trace(f"Handling a raised error {error} from {ctx.command}")

        if isinstance(error, BadArgument):
            embed = self._get_error_embed("Bad argument", str(error))
            await ctx.send(embed=embed)
            return
        elif isinstance(error, CommandNotFound):
            embed = self._get_error_embed("Command not found", str(error))
            await ctx.send(embed=embed)
            return

        # If we haven't handled it by this point, it is considered an unexpected/handled error.
        await ctx.send(
            f"Sorry, an unexpected error occurred. Please let us know!\n\n"
            f"```{error.__class__.__name__}: {error}```"
        )
        log.error(f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}", exc_info=error)


async def setup(bot: SirRobin) -> None:
    """Load the ErrorHandler cog."""
    await bot.add_cog(ErrorHandler(bot))
