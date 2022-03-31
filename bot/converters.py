from typing import Union

from discord.ext import commands
from discord.ext.commands import BadArgument, Context, Converter
from discord.utils import escape_markdown

SourceType = Union[commands.HelpCommand, commands.Command, commands.Cog, str, commands.ExtensionNotLoaded]


class SourceConverter(Converter):
    """Convert an argument into a help command, command, or cog."""

    @staticmethod
    async def convert(ctx: Context, argument: str) -> SourceType:
        """Convert argument into source object."""
        if argument.lower() == "help":
            return ctx.bot.help_command

        if cog := ctx.bot.get_cog(argument):
            return cog

        if cmd := ctx.bot.get_command(argument):
            return cmd

        escaped_arg = escape_markdown(argument)

        raise BadArgument(
            f"Unable to convert '{escaped_arg}' to valid command or Cog."
        )
