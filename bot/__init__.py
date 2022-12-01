import asyncio
import os

from pydis_core.utils import apply_monkey_patches

from bot.bot import SirRobin
from bot.log import setup_logging

# On Windows, the selector event loop is required for aiodns.
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


setup_logging()

# Apply all monkey patches from bot core.
apply_monkey_patches()

instance: "SirRobin" = None  # Global SirRobin instance.
