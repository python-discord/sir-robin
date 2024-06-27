from collections.abc import Callable, Container

from discord.ext import commands
from discord.ext.commands import Context

from bot import constants
from bot.log import get_logger
from bot.utils.exceptions import CodeJamCategoryCheckFailure, InWhitelistCheckFailure, SilentChannelFailure

log = get_logger(__name__)


def in_code_jam_category(code_jam_category_name: str) -> Callable:
    """Raises `CodeJamCategoryCheckFailure` when the command is invoked outside the Code Jam categories."""
    async def predicate(ctx: commands.Context) -> bool:  # noqa: RUF029
        if not ctx.guild:
            return False
        if not ctx.message.channel.category:
            return False
        if ctx.message.channel.category.name == code_jam_category_name:
            return True
        log.trace(f"{ctx.author} tried to invoke {ctx.command.name} outside of the Code Jam categories.")
        raise CodeJamCategoryCheckFailure

    return commands.check(predicate)


def in_whitelist_check(
    ctx: Context,
    channels: Container[int] = (),
    categories: Container[int] = (),
    roles: Container[int] = (),
    redirect: int | None = constants.Channels.sir_lancebot_playground,
    role_override: Container[int] = (),
    fail_silently: bool = False,
) -> bool:
    """
    Check if a command was issued in a whitelisted context.

    The whitelists that can be provided are:

    - `channels`: a container with channel ids for whitelisted channels
    - `categories`: a container with category ids for whitelisted categories
    - `roles`: a container with role ids for whitelisted roles

    If the command was invoked in a context that was not whitelisted, the member is either
    redirected to the `redirect` channel that was passed (default: #bot-commands) or simply
    told that they're not allowed to use this particular command (if `None` was passed).
    """
    # If the author has an override role, they can run this command anywhere
    if role_override:
        for role in ctx.author.roles:
            if role.id in role_override:
                log.info(f"{ctx.author} is allowed to use {ctx.command.name} anywhere")
                return True

    if redirect and redirect not in channels:
        # It does not make sense for the channel whitelist to not contain the redirection
        # channel (if applicable). That's why we add the redirection channel to the `channels`
        # container if it's not already in it. As we allow any container type to be passed,
        # we first create a tuple in order to safely add the redirection channel.
        #
        # Note: It's possible for the redirect channel to be in a whitelisted category, but
        # there's no easy way to check that and as a channel can easily be moved in and out of
        # categories, it's probably not wise to rely on its category in any case.
        channels = tuple(channels) + (redirect,)

    if channels and ctx.channel.id in channels:
        log.trace(f"{ctx.author} may use the `{ctx.command.name}` command as they are in a whitelisted channel.")
        return True

    # Only check the category id if we have a category whitelist and the channel has a `category_id`
    if categories and hasattr(ctx.channel, "category_id") and ctx.channel.category_id in categories:
        log.trace(f"{ctx.author} may use the `{ctx.command.name}` command as they are in a whitelisted category.")
        return True

    category = getattr(ctx.channel, "category", None)
    if category and category.name == constants.Categories.summer_code_jam:
        log.trace(f"{ctx.author} may use the `{ctx.command.name}` command as they are in a codejam team channel.")
        return True

    # Only check the roles whitelist if we have one and ensure the author's roles attribute returns
    # an iterable to prevent breakage in DM channels (for if we ever decide to enable commands there).
    if roles and any(r.id in roles for r in getattr(ctx.author, "roles", ())):
        log.trace(f"{ctx.author} may use the `{ctx.command.name}` command as they have a whitelisted role.")
        return True

    log.trace(f"{ctx.author} may not use the `{ctx.command.name}` command within this context.")

    # Some commands are secret, and should produce no feedback at all.
    if not fail_silently:
        raise InWhitelistCheckFailure(redirect)
    raise SilentChannelFailure("Wrong channel, silently fail")
