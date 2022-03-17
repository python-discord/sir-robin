import logging
import sys

from botcore.utils.logging import get_logger


def setup_logging() -> None:
    """Configure logging for the bot."""
    root_log = get_logger()
    root_log.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.DEBUG)
    format_string = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    ch.setFormatter(format_string)
    root_log.addHandler(ch)

    get_logger("discord").setLevel(logging.WARNING)

    # Set back to the default of INFO even if asyncio's debug mode is enabled.
    get_logger("asyncio").setLevel(logging.INFO)

    root_log.info("Logging initialization complete.")
