from typing import Union

from discord.ext import commands
from discord.ext.commands import BadArgument, Context, Converter
from discord.utils import escape_markdown

SourceType = Union[commands.HelpCommand, commands.Command, commands.Cog, str, commands.ExtensionNotLoaded]


class SourceConverter(Converter):
    """Convert an argument into a help command, tag, command, or cog."""

    @staticmethod
    async def convert(ctx: Context, argument: str) -> SourceType:
        """Convert argument into source object."""
        if argument.lower() == "help":
            return ctx.bot.help_command

        cog = ctx.bot.get_cog(argument)
        if cog:
            return cog

        cmd = ctx.bot.get_command(argument)
        if cmd:
            return cmd

        tags_cog = ctx.bot.get_cog("Tags")
        show_tag = True

        if not tags_cog:
            show_tag = False
        elif argument.lower() in tags_cog._cache:
            return argument.lower()

        escaped_arg = escape_markdown(argument)

        raise BadArgument(
            f"Unable to convert '{escaped_arg}' to valid command{', tag,' if show_tag else ''} or Cog."
        )
