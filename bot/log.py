import logging
import sys

import sentry_sdk
from pydis_core.utils.logging import TRACE_LEVEL, get_logger
from sentry_sdk.integrations.logging import LoggingIntegration

from bot.constants import Bot, GIT_SHA


def setup_logging() -> None:
    """Configure logging for the bot."""
    root_log = get_logger()
    root_log.setLevel(TRACE_LEVEL if Bot.trace_logging else logging.DEBUG if Bot.debug else logging.INFO)

    ch = logging.StreamHandler(stream=sys.stdout)
    format_string = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    ch.setFormatter(format_string)
    root_log.addHandler(ch)

    get_logger("discord").setLevel(logging.WARNING)

    # Set back to the default of INFO even if asyncio's debug mode is enabled.
    get_logger("asyncio").setLevel(logging.INFO)

    root_log.info("Logging initialization complete.")


def setup_sentry() -> None:
    """Set up the Sentry logging integrations."""
    sentry_logging = LoggingIntegration(
        level=logging.DEBUG,
        event_level=logging.WARNING
    )

    sentry_sdk.init(
        dsn=Bot.sentry_dsn,
        integrations=[
            sentry_logging,
        ],
        release=f"sir-robin@{GIT_SHA}",
        traces_sample_rate=0.5,
        profiles_sample_rate=0.5,
    )
