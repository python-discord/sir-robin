import asyncio
import functools
from calendar import Month
from collections.abc import Callable, Container

from discord.ext import commands
from discord.ext.commands import Command, Context
from pydis_core.utils import logging

from bot.constants import Channels
from bot.utils import human_months, resolve_current_month
from bot.utils.checks import in_whitelist_check
from bot.utils.exceptions import InMonthCheckFailure, SilentRoleFailure

ONE_DAY = 24 * 60 * 60

log = logging.get_logger(__name__)


def seasonal_task(*allowed_months: Month, sleep_time: float | int = ONE_DAY) -> Callable:
    """
    Perform the decorated method periodically in `allowed_months`.

    This provides a convenience wrapper to avoid code repetition where some task shall
    perform an operation repeatedly in a constant interval, but only in specific months.

    The decorated function will be called once every `sleep_time` seconds while
    the current UTC month is in `allowed_months`. Sleep time defaults to 24 hours.

    The wrapped task is responsible for waiting for the bot to be ready, if necessary.
    """
    def decorator(task_body: Callable) -> Callable:
        @functools.wraps(task_body)
        async def decorated_task(*args, **kwargs) -> None:
            """Call `task_body` once every `sleep_time` seconds in `allowed_months`."""
            log.info(f"Starting seasonal task {task_body.__qualname__} ({human_months(allowed_months)})")

            while True:
                current_month = resolve_current_month()

                if current_month in allowed_months:
                    await task_body(*args, **kwargs)
                else:
                    log.debug(f"Seasonal task {task_body.__qualname__} sleeps in {current_month!s}")

                await asyncio.sleep(sleep_time)
        return decorated_task
    return decorator


def in_month_listener(*allowed_months: Month) -> Callable:
    """
    Shield a listener from being invoked outside of `allowed_months`.

    The check is performed against current UTC month.
    """
    def decorator(listener: Callable) -> Callable:
        @functools.wraps(listener)
        async def guarded_listener(*args, **kwargs) -> None:
            """Wrapped listener will abort if not in allowed month."""
            current_month = resolve_current_month()

            if current_month in allowed_months:
                # Propagate return value although it should always be None
                return await listener(*args, **kwargs)

            log.debug(f"Guarded {listener.__qualname__} from invoking in {current_month!s}")
            return None
        return guarded_listener
    return decorator


def in_month_command(*allowed_months: Month) -> Callable:
    """
    Check whether the command was invoked in one of `enabled_months`.

    Uses the current UTC month at the time of running the predicate.
    """
    async def predicate(ctx: Context) -> bool:
        current_month = resolve_current_month()
        can_run = current_month in allowed_months

        log.debug(
            f"Command '{ctx.command}' is locked to months {human_months(allowed_months)}. "
            f"Invoking it in month {current_month!s} is {'allowed' if can_run else 'disallowed'}."
        )
        if can_run:
            return True
        raise InMonthCheckFailure(f"Command can only be used in {human_months(allowed_months)}")

    return commands.check(predicate)


def in_month(*allowed_months: Month) -> Callable:
    """
    Universal decorator for season-locking commands and listeners alike.

    This only serves to determine whether the decorated callable is a command,
    a listener, or neither. It then delegates to either `in_month_command`,
    or `in_month_listener`, or raises TypeError, respectively.

    Please note that in order for this decorator to correctly determine whether
    the decorated callable is a cmd or listener, it **has** to first be turned
    into one. This means that this decorator should always be placed **above**
    the d.py one that registers it as either.

    This will decorate groups as well, as those subclass Command. In order to lock
    all subcommands of a group, its `invoke_without_command` param must **not** be
    manually set to True - this causes a circumvention of the group's callback
    and the seasonal check applied to it.
    """
    def decorator(callable_: Callable) -> Callable:
        # Functions decorated as commands are turned into instances of `Command`
        if isinstance(callable_, Command):
            log.debug(f"Command {callable_.qualified_name} will be locked to {human_months(allowed_months)}")
            actual_deco = in_month_command(*allowed_months)

        # D.py will assign this attribute when `callable_` is registered as a listener
        elif hasattr(callable_, "__cog_listener__"):
            log.debug(f"Listener {callable_.__qualname__} will be locked to {human_months(allowed_months)}")
            actual_deco = in_month_listener(*allowed_months)

        # Otherwise we're unsure exactly what has been decorated
        # This happens before the bot starts, so let's just raise
        else:
            raise TypeError(f"Decorated object {callable_} is neither a command nor a listener")

        return actual_deco(callable_)
    return decorator


def with_role(*role_ids: int, fail_silently: bool = False) -> Callable:
    """Check to see whether the invoking user has any of the roles specified in role_ids."""
    async def predicate(ctx: Context) -> bool:
        log.debug(
            "Checking if %s has one of the following role IDs %s. Fail silently is set to %s.",
            ctx.author,
            role_ids,
            fail_silently
        )
        try:
            return await commands.has_any_role(*role_ids).predicate(ctx)
        except commands.MissingAnyRole as e:
            if fail_silently:
                raise SilentRoleFailure from e
            raise
    return commands.check(predicate)


def in_whitelist(
    *,
    channels: Container[int] = (),
    categories: Container[int] = (),
    roles: Container[int] = (),
    redirect: Container[int] | None = (Channels.sir_lancebot_playground,),
    role_override: Container[int] | None = (),
    fail_silently: bool = False
) -> Callable:
    """
    Check if a command was issued in a whitelisted context.

    The whitelists that can be provided are:
    - `channels`: a container with channel ids for allowed channels
    - `categories`: a container with category ids for allowed categories
    - `roles`: a container with role ids for allowed roles

    If the command was invoked in a non whitelisted manner, they are redirected
    to the `redirect` channel(s) that is passed (default is #sir-lancebot-playground) or
    told they are not allowd to use that particular commands (if `None` was passed)
    """
    def predicate(ctx: Context) -> bool:
        return in_whitelist_check(ctx, channels, categories, roles, redirect, role_override, fail_silently)

    return commands.check(predicate)


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
