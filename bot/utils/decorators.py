import random
from asyncio import Lock
from collections.abc import Container
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Optional
from weakref import WeakValueDictionary

from botcore.utils.logging import get_logger
from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import CheckFailure, Context

from bot.constants import (ERROR_REPLIES, WHITELISTED_CHANNELS, Channels,
                           season_lock_config)
from bot.utils.checks import in_whitelist_check
from bot.utils.exceptions import (InIntervalCheckFailure,
                                  MalformedSeasonLockConfigError)

ONE_DAY = 24 * 60 * 60

log = get_logger(__name__)


class InChannelCheckFailure(CheckFailure):
    """Check failure when the user runs a command in a non-whitelisted channel."""

    pass


def in_interval(unique_id: str) -> Callable:
    """Shield a command from being invoked outside the interval specified in the config with the id of `unique_id`."""

    async def predicate(ctx: commands.Context) -> bool:
        """Wrapped command will abort if not in allowed season."""
        if config := season_lock_config.get(unique_id):
            now = datetime.now(tz=timezone.utc)
            try:
                start_date = datetime(
                    year=now.year,
                    month=config["start"]["month"],
                    day=config["start"]["day"],
                    hour=0,
                    minute=0,
                    tzinfo=timezone.utc
                )
                end_date = datetime(
                    year=now.year if config["end"]["month"] >= config["start"]["month"] else now.year + 1,
                    month=config["end"]["month"],
                    day=config["end"]["day"],
                    hour=23,
                    minute=59,
                    tzinfo=timezone.utc
                )
            except KeyError as e:
                raise MalformedSeasonLockConfigError(
                    "Malformed season_lock config, invalid values were provided.") from e
            else:
                if start_date <= now <= end_date:
                    return True
                else:
                    log.info(
                        f"Command {ctx.command} is locked from \n "
                        f"{start_date.strftime('%Y.%m.%d')} until {end_date.strftime('%Y.%m.%d')}!"
                    )
                    raise InIntervalCheckFailure(
                        f"Command {ctx.command} is locked until {start_date.strftime('%Y.%m.%d')}"
                    )

    return commands.check(predicate)


def with_role(*role_ids: int) -> Callable:
    """Check to see whether the invoking user has any of the roles specified in role_ids."""

    async def predicate(ctx: Context) -> bool:
        if not ctx.guild:  # Return False in a DM
            log.debug(
                f"{ctx.author} tried to use the '{ctx.command.name}'command from a DM. "
                "This command is restricted by the with_role decorator. Rejecting request."
            )
            return False

        for role in ctx.author.roles:
            if role.id in role_ids:
                log.debug(f"{ctx.author} has the '{role.name}' role, and passes the check.")
                return True

        log.debug(
            f"{ctx.author} does not have the required role to use "
            f"the '{ctx.command.name}' command, so the request is rejected."
        )
        return False

    return commands.check(predicate)


def without_role(*role_ids: int) -> Callable:
    """Check whether the invoking user does not have all of the roles specified in role_ids."""

    async def predicate(ctx: Context) -> bool:
        if not ctx.guild:  # Return False in a DM
            log.debug(
                f"{ctx.author} tried to use the '{ctx.command.name}' command from a DM. "
                "This command is restricted by the without_role decorator. Rejecting request."
            )
            return False

        author_roles = [role.id for role in ctx.author.roles]
        check = all(role not in author_roles for role in role_ids)
        log.debug(
            f"{ctx.author} tried to call the '{ctx.command.name}' command. "
            f"The result of the without_role check was {check}."
        )
        return check

    return commands.check(predicate)


def whitelist_check(**default_kwargs: Container[int]) -> Callable[[Context], bool]:
    """
    Checks if a message is sent in a whitelisted context.

    All arguments from `in_whitelist_check` are supported, with the exception of "fail_silently".
    If `whitelist_override` is present, it is added to the global whitelist.
    """

    def predicate(ctx: Context) -> bool:
        kwargs = default_kwargs.copy()
        allow_dms = False

        # Update kwargs based on override
        if hasattr(ctx.command.callback, "override"):
            # Handle DM invocations
            allow_dms = ctx.command.callback.override_dm

            # Remove default kwargs if reset is True
            if ctx.command.callback.override_reset:
                kwargs = {}
                log.debug(
                    f"{ctx.author} called the '{ctx.command.name}' command and "
                    f"overrode default checks."
                )

            # Merge overwrites and defaults
            for arg in ctx.command.callback.override:
                default_value = kwargs.get(arg)
                new_value = ctx.command.callback.override[arg]

                # Skip values that don't need merging, or can't be merged
                if default_value is None or isinstance(arg, int):
                    kwargs[arg] = new_value

                # Merge containers
                elif isinstance(default_value, Container):
                    if isinstance(new_value, Container):
                        kwargs[arg] = (*default_value, *new_value)
                    else:
                        kwargs[arg] = new_value

            log.debug(
                f"Updated default check arguments for '{ctx.command.name}' "
                f"invoked by {ctx.author}."
            )

        if ctx.guild is None:
            log.debug(f"{ctx.author} tried using the '{ctx.command.name}' command from a DM.")
            result = allow_dms
        else:
            log.trace(f"Calling whitelist check for {ctx.author} for command {ctx.command.name}.")
            result = in_whitelist_check(ctx, fail_silently=True, **kwargs)

        # Return if check passed
        if result:
            log.debug(
                f"{ctx.author} tried to call the '{ctx.command.name}' command "
                f"and the command was used in an overridden context."
            )
            return result

        log.debug(
            f"{ctx.author} tried to call the '{ctx.command.name}' command. "
            f"The whitelist check failed."
        )

        # Raise error if the check did not pass
        channels = set(kwargs.get("channels") or {})
        categories = kwargs.get("categories")

        # Only output override channels + sir_lancebot_playground
        if channels:
            default_whitelist_channels = set(WHITELISTED_CHANNELS)
            default_whitelist_channels.discard(Channels.sir_lancebot_playground)
            channels.difference_update(default_whitelist_channels)

        # Add all whitelisted category channels, but skip if we're in DMs
        if categories and ctx.guild is not None:
            for category_id in categories:
                category = ctx.guild.get_channel(category_id)
                if category is None:
                    continue

                channels.update(channel.id for channel in category.text_channels)

        if channels:
            channels_str = ", ".join(f"<#{c_id}>" for c_id in channels)
            message = f"Sorry, but you may only use this command within {channels_str}."
        else:
            message = "Sorry, but you may not use this command."

        raise InChannelCheckFailure(message)

    return predicate


def whitelist_override(bypass_defaults: bool = False, allow_dm: bool = False, **kwargs: Container[int]) -> Callable:
    """
    Override global whitelist context, with the kwargs specified.

    All arguments from `in_whitelist_check` are supported, with the exception of `fail_silently`.
    Set `bypass_defaults` to True if you want to completely bypass global checks.

    Set `allow_dm` to True if you want to allow the command to be invoked from within direct messages.
    Note that you have to be careful with any references to the guild.

    This decorator has to go before (below) below the `command` decorator.
    """

    def inner(func: Callable) -> Callable:
        func.override = kwargs
        func.override_reset = bypass_defaults
        func.override_dm = allow_dm
        return func

    return inner


def locked() -> Optional[Callable]:
    """
    Allows the user to only run one instance of the decorated command at a time.

    Subsequent calls to the command from the same author are ignored until the command has completed invocation.

    This decorator has to go before (below) the `command` decorator.
    """

    def wrap(func: Callable) -> Optional[Callable]:
        func.__locks = WeakValueDictionary()

        @wraps(func)
        async def inner(self: Callable, ctx: Context, *args, **kwargs) -> Optional[Callable]:
            lock = func.__locks.setdefault(ctx.author.id, Lock())
            if lock.locked():
                embed = Embed()
                embed.colour = Colour.red()

                log.debug("User tried to invoke a locked command.")
                embed.description = (
                    "You're already using this command. Please wait until "
                    "it is done before you use it again."
                )
                embed.title = random.choice(ERROR_REPLIES)
                await ctx.send(embed=embed)
                return

            async with func.__locks.setdefault(ctx.author.id, Lock()):
                return await func(self, ctx, *args, **kwargs)

        return inner

    return wrap
