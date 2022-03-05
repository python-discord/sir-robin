import json
from os import environ
from pathlib import Path
from typing import NamedTuple, Optional

from botcore.utils.logging import get_logger

log = get_logger(__name__)


class MalformedSeasonLockConfigError(Exception):
    """Thrown when an invalid or malformed config is provided."""

    pass


class Channels(NamedTuple):
    bot_commands = 267659945086812160
    devlog = int(environ.get("CHANNEL_DEVLOG", 622895325144940554))
    sir_lancebot_playground = int(environ.get("CHANNEL_COMMUNITY_BOT_COMMANDS", 607247579608121354))


class Client(NamedTuple):
    name = "Sir Robin"
    guild = int(environ.get("BOT_GUILD", 267624335836053506))
    prefix = environ.get("PREFIX", "&")
    token = environ.get("BOT_TOKEN")
    debug = environ.get("BOT_DEBUG", "true").lower() == "true"
    in_ci = environ.get("IN_CI", "false").lower() == "true"
    use_fake_redis = environ.get("USE_FAKEREDIS", "false").lower() == "true"
    github_bot_repo = "https://github.com/python-discord/sir-robin"


def read_config() -> Optional[dict]:
    """
    Read the season_lock config in from the JSON file.

    If the config is invalid an `MalformedSeasonLockConfigError` is raised
    """
    if Path("season_lock.json").exists():
        log.info("Found `season_lock.yml` file, loading constants from it.")
        try:
            with open("season_lock.json") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise MalformedSeasonLockConfigError from e
        else:
            return config


season_lock_config = read_config()
