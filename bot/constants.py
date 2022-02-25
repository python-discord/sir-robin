from os import environ
from typing import NamedTuple


class Channels(NamedTuple):
    bot_commands = 267659945086812160
    sir_lancebot_playground = int(environ.get("CHANNEL_COMMUNITY_BOT_COMMANDS", 607247579608121354))


class Client(NamedTuple):
    name = "Sir Robin"
    guild = int(environ.get("BOT_GUILD", 267624335836053506))
    prefix = environ.get("PREFIX", "&")
    token = environ.get("BOT_TOKEN")
    debug = environ.get("BOT_DEBUG", "true").lower() == "true"
    in_ci = environ.get("IN_CI", "false").lower() == "true"
    github_bot_repo = "https://github.com/python-discord/sir-robin"
