from os import environ
from typing import NamedTuple


class Channels(NamedTuple):
    bot_commands = 267659945086812160
    devlog = int(environ.get("CHANNEL_DEVLOG", 622895325144940554))
    code_jam_planning = int(environ.get("CHANNEL_CODE_JAM_PLANNING", 490217981872177157))
    sir_lancebot_playground = int(environ.get("CHANNEL_COMMUNITY_BOT_COMMANDS", 607247579608121354))


class Categories(NamedTuple):
    summer_code_jam = int(environ.get("CATEGORY_SUMMER_CODE_JAM", 861692638540857384))


class Emojis(NamedTuple):
    check_mark = "\u2705"


class Roles(NamedTuple):
    admins = int(environ.get("ROLE_ADMINS", 267628507062992896))
    code_jam_event_team = int(environ.get("ROLE_CODE_JAM_EVENT_TEAM", 787816728474288181))
    events_lead = int(environ.get("ROLE_EVENTS_LEAD", 778361735739998228))


class Client(NamedTuple):
    name = "Sir Robin"
    guild = int(environ.get("BOT_GUILD", 267624335836053506))
    prefix = environ.get("PREFIX", "&")
    token = environ.get("BOT_TOKEN")
    debug = environ.get("BOT_DEBUG", "true").lower() == "true"
    in_ci = environ.get("IN_CI", "false").lower() == "true"
    use_fake_redis = environ.get("USE_FAKEREDIS", "false").lower() == "true"
    code_jam_api = environ.get("CODE_JAM_API", "http://code-jam-management.default.svc.cluster.local:8000")
    code_jam_token = environ.get("CODE_JAM_API_KEY", "badbot13m0n8f570f942013fc818f234916ca531")
    github_bot_repo = "https://github.com/python-discord/sir-robin"
