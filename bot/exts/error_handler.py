from discord import Colour, Embed
from discord.ext.commands import (BadArgument, Cog, CommandError,
                                  CommandNotFound, Context, MissingAnyRole,
                                  MissingRequiredArgument)

from bot.bot import SirRobin
from bot.log import get_logger
from bot.utils.exceptions import CodeJamCategoryCheckFailure

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

        # We could handle the subclasses of UserInputError errors together, using the error
        # name as the embed title. Before doing this we would have to verify that all messages
        # attached to subclasses of this error are human-readable, as they are user facing.
        if isinstance(error, BadArgument):
            embed = self._get_error_embed("Bad argument", str(error))
            await ctx.send(embed=embed)
            return
        elif isinstance(error, CommandNotFound):
            embed = self._get_error_embed("Command not found", str(error))
            await ctx.send(embed=embed)
            return
        elif isinstance(error, MissingRequiredArgument):
            embed = self._get_error_embed("Missing required argument", str(error))
            await ctx.send(embed=embed)
            return
        elif isinstance(error, MissingAnyRole):
            embed = self._get_error_embed("Permission error", "You are not allowed to use this command!")
            await ctx.send(embed=embed)
            return
        elif isinstance(error, CodeJamCategoryCheckFailure):
            # Silently fail, as SirRobin should not respond
            # to any of the CJ related commands outside of the CJ categories.
            log.error(exc_info=error)
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
