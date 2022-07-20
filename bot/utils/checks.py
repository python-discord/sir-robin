from typing import Callable, NoReturn, Union

import discord
from discord.ext import commands

from bot.log import get_logger
from bot.utils.exceptions import CodeJamCategoryCheckFailure

log = get_logger(__name__)


def in_code_jam_category(code_jam_category_name: str) -> Callable:
    """Raises `CodeJamCategoryCheckFailure` when the command is invoked outside of the Code Jam categories."""
    async def predicate(ctx: commands.Context) -> Union[bool, NoReturn]:
        if not ctx.guild:
            return False
        if not ctx.message.channel.category:
            return False
        code_jam_categories = filter(lambda category: category.name == code_jam_category_name, ctx.guild.categories)
        if ctx.message.channel.category in code_jam_categories:
            return True
        log.trace(f"{ctx.author} tried to invoke {ctx.command.name} outside of the Code Jam categories.")
        raise CodeJamCategoryCheckFailure()

    return commands.check(predicate)


def message_is_in_code_jam_category(
        message: discord.Message,
        code_jam_category_name: str,
        ctx: commands.Context
) -> bool:
    """Returns True if the message's channel is in one of the Code Jam Categories."""
    code_jam_categories = filter(lambda category: category.name == code_jam_category_name, ctx.guild.categories)
    if message.channel.category in code_jam_categories:
        return True
    return False
