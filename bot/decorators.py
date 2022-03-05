from typing import Callable
from .constants import season_lock_config, MalformedSeasonLockConfigError
from datetime import datetime, timezone

from disnake.ext import commands
from disnake.ext.commands import CheckFailure
from botcore.utils.logging import get_logger

log = get_logger(__name__)


class InIntervalCheckFailure(CheckFailure):
    """Check failure for when a command is invoked outside of its allowed month."""

    pass


def in_interval(unique_id: str) -> Callable:
    """
    Shield a command from being invoked outside the interval specified in the config
    with the id of `unique_id`.
    """

    async def predicate(ctx: commands.Context) -> bool:
        """Wrapped command will abort if not in allowed season"""
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
                log.info(start_date)
                log.info(end_date)
            except KeyError as e:
                raise MalformedSeasonLockConfigError(
                    "Malformed season_lock config, invalid values were provided.") from e
            else:
                log.debug(start_date <= now <= end_date)
                if start_date <= now <= end_date:
                    return True
                else:
                    raise InIntervalCheckFailure(
                        f"Command {ctx.command} is locked to the interval between "
                        f"{start_date.strftime('%Y.%m.%d')} and {end_date.strftime('%Y.%m.%d')}!"
                    ) from None

    return commands.check(predicate)
