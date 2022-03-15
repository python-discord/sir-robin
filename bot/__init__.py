from botcore.utils import apply_monkey_patches
from botcore.utils.logging import get_logger

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
