from os import environ
from typing import NamedTuple


class Channels(NamedTuple):
    advent_of_code = int(environ.get("AOC_CHANNEL_ID", 897932085766004786))
    advent_of_code_commands = int(environ.get("AOC_COMMANDS_CHANNEL_ID", 897932607545823342))
    bot_commands = 267659945086812160
    community_meta = 267659945086812160
    organisation = 551789653284356126
    devlog = int(environ.get("CHANNEL_DEVLOG", 622895325144940554))
    dev_contrib = 635950537262759947
    mod_meta = 775412552795947058
    mod_tools = 775413915391098921
    off_topic_0 = 291284109232308226
    off_topic_1 = 463035241142026251
    off_topic_2 = 463035268514185226
    sir_lancebot_playground = int(environ.get("CHANNEL_COMMUNITY_BOT_COMMANDS", 607247579608121354))
    voice_chat_0 = 412357430186344448
    voice_chat_1 = 799647045886541885
    staff_voice = 541638762007101470
    reddit = int(environ.get("CHANNEL_REDDIT", 458224812528238616))


class Client(NamedTuple):
    name = "Sir Robin"
    guild = int(environ.get("BOT_GUILD", 267624335836053506))
    prefix = environ.get("PREFIX", "&")
    token = environ.get("BOT_TOKEN")
    debug = environ.get("BOT_DEBUG", "true").lower() == "true"
    in_ci = environ.get("IN_CI", "false").lower() == "true"
    github_bot_repo = "https://github.com/python-discord/sir-robin"
    # Override seasonal locks: 1 (January) to 12 (December)
    month_override = int(environ["MONTH_OVERRIDE"]) if "MONTH_OVERRIDE" in environ else None
