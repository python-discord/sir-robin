from discord import Colour, Embed
from discord.ext.commands import (
    Cog,
    CommandError,
    Context,
    errors,
)

from bot.bot import SirRobin
from bot.log import get_logger
from bot.utils.exceptions import (
    InMonthCheckFailure,
    InWhitelistCheckFailure,
    SilentCheckFailure,
)

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

        if isinstance(error, errors.UserInputError):
            await self.handle_user_input_error(ctx, error)
            return

        if isinstance(error, errors.CheckFailure):
            await self.handle_check_failure(ctx, error)
            return

        if isinstance(error, errors.CommandNotFound):
            embed = self._get_error_embed("Command not found", str(error))
        else:
            # If we haven't handled it by this point, it is considered an unexpected/handled error.
            log.exception(f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}")
            embed = self._get_error_embed(
                "Unexpected error",
                "Sorry, an unexpected error occurred. Please let us know!\n\n"
                f"```{error.__class__.__name__}: {error}```"
            )
        await ctx.send(embed=embed)

    async def handle_user_input_error(self, ctx: Context, e: errors.UserInputError) -> None:
        """
        Send an error message in `ctx` for UserInputError, sometimes invoking the help command too.

        * MissingRequiredArgument: send an error message with arg name and the help command
        * TooManyArguments: send an error message and the help command
        * BadArgument: send an error message and the help command
        * BadUnionArgument: send an error message including the error produced by the last converter
        * ArgumentParsingError: send an error message
        * Other: send an error message and the help command
        """
        if isinstance(e, errors.MissingRequiredArgument):
            embed = self._get_error_embed("Missing required argument", e.param.name)
        elif isinstance(e, errors.TooManyArguments):
            embed = self._get_error_embed("Too many arguments", str(e))
        elif isinstance(e, errors.BadArgument):
            embed = self._get_error_embed("Bad argument", str(e))
        elif isinstance(e, errors.BadUnionArgument):
            embed = self._get_error_embed("Bad argument", f"{e}\n{e.errors[-1]}")
        elif isinstance(e, errors.ArgumentParsingError):
            embed = self._get_error_embed("Argument parsing error", str(e))
        else:
            embed = self._get_error_embed(
                "Input error",
                "Something about your input seems off. Check the arguments and try again."
            )

        await ctx.send(embed=embed)

    async def handle_check_failure(self, ctx: Context, e: errors.CheckFailure) -> None:
        """
        Send an error message in `ctx` for certain types of CheckFailure.

        The following types are handled:

        * BotMissingPermissions
        * BotMissingRole
        * BotMissingAnyRole
        * MissingAnyRole
        * InMonthCheckFailure
        * SilentCheckFailure
        * InWhitelistCheckFailure
        * NoPrivateMessage
        """
        bot_missing_errors = (
            errors.BotMissingPermissions,
            errors.BotMissingRole,
            errors.BotMissingAnyRole
        )

        if isinstance(e, SilentCheckFailure):
            # Silently fail, SirRobin should not respond
            log.info(
                f"{ctx.author} ({ctx.author.id}) tried to run {ctx.command} "
                f"but hit a silent check failure {e.__class__.__name__}",
            )
            return

        if isinstance(e, bot_missing_errors):
            embed = self._get_error_embed("Permission error", "I don't have the permission I need to do that!")
        elif isinstance(e, errors.MissingAnyRole):
            embed = self._get_error_embed("Permission error", "You are not allowed to use this command!")
        elif isinstance(e, InMonthCheckFailure):
            embed = self._get_error_embed("Command not available", str(e))
        elif isinstance(e, InWhitelistCheckFailure):
            embed = self._get_error_embed("Wrong Channel", str(e))
        elif isinstance(e, errors.NoPrivateMessage):
            embed = self._get_error_embed("Wrong channel", "This command can not be ran in DMs@")
        else:
            embed = self._get_error_embed(
                "Unexpected check failure",
                "Sorry, an unexpected check error occurred. Please let us know!\n\n"
                f"```{e.__class__.__name__}: {e}```"
            )
        await ctx.send(embed=embed)


async def setup(bot: SirRobin) -> None:
    """Load the ErrorHandler cog."""
    await bot.add_cog(ErrorHandler(bot))
