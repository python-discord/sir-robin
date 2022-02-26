from botcore.utils.logging import get_logger
from botcore.utils.monkey_patches import apply_monkey_patches

from bot.log import setup_logging

log = get_logger(__name__)

try:
    from dotenv import load_dotenv
    log.debug("Found .env file, loading environment variables from it.")
    load_dotenv(override=True)
except ModuleNotFoundError:
    pass


setup_logging()

# Apply all monkey patches from bot core.
apply_monkey_patches()
