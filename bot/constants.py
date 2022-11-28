import dataclasses
from datetime import datetime
import enum
import logging
from os import environ
from typing import NamedTuple

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ModuleNotFoundError:
    pass

log = logging.getLogger(__name__)


@dataclasses.dataclass
class AdventOfCodeLeaderboard:
    id: str
    _session: str
    join_code: str

    # If we notice that the session for this board expired, we set
    # this attribute to `True`. We will emit a Sentry error so we
    # can handle it, but, in the meantime, we'll try using the
    # fallback session to make sure the commands still work.
    use_fallback_session: bool = False

    @property
    def session(self) -> str:
        """Return either the actual `session` cookie or the fallback cookie."""
        if self.use_fallback_session:
            log.trace(f"Returning fallback cookie for board `{self.id}`.")
            return AdventOfCode.fallback_session

        return self._session


def _parse_aoc_leaderboard_env() -> dict[str, AdventOfCodeLeaderboard]:
    """
    Parse the environment variable containing leaderboard information.

    A leaderboard should be specified in the format `id,session,join_code`,
    without the backticks. If more than one leaderboard needs to be added to
    the constant, separate the individual leaderboards with `::`.

    Example ENV: `id1,session1,join_code1::id2,session2,join_code2`
    """
    raw_leaderboards = environ.get("AOC_LEADERBOARDS", "")
    if not raw_leaderboards:
        return {}

    leaderboards = {}
    for leaderboard in raw_leaderboards.split("::"):
        leaderboard_id, session, join_code = leaderboard.split(",")
        leaderboards[leaderboard_id] = AdventOfCodeLeaderboard(leaderboard_id, session, join_code)

    return leaderboards


class AdventOfCode:
    # Information for the several leaderboards we have
    leaderboards = _parse_aoc_leaderboard_env()
    staff_leaderboard_id = environ.get("AOC_STAFF_LEADERBOARD_ID", "")
    fallback_session = environ.get("AOC_FALLBACK_SESSION", "")

    # Other Advent of Code constants
    ignored_days = environ.get("AOC_IGNORED_DAYS", "").split(",")
    leaderboard_displayed_members = 10
    leaderboard_cache_expiry_seconds = 1800
    max_day_and_star_results = 15
    year = int(environ.get("AOC_YEAR", datetime.utcnow().year))
    role_id = int(environ.get("AOC_ROLE_ID", 518565788744024082))


class Channels(NamedTuple):
    advent_of_code = int(environ.get("AOC_CHANNEL_ID", 897932085766004786))
    advent_of_code_commands = int(environ.get("AOC_COMMANDS_CHANNEL_ID", 897932607545823342))
    bot_commands = 267659945086812160
    devlog = int(environ.get("CHANNEL_DEVLOG", 622895325144940554))
    code_jam_planning = int(environ.get("CHANNEL_CODE_JAM_PLANNING", 490217981872177157))
    summer_aoc_main = int(environ.get("SUMMER_AOC_MAIN_CHANNEL", 988979042847957042))
    summer_aoc_discussion = int(environ.get("SUMMER_AOC_DISCUSSION", 996438901331861554))
    sir_lancebot_playground = int(environ.get("CHANNEL_COMMUNITY_BOT_COMMANDS", 607247579608121354))
    summer_code_jam = int(environ.get("CATEGORY_SUMMER_CODE_JAM", 987738098525937745))
    summer_code_jam_announcements = int(environ.get("SUMMER_CODE_JAM_ANNOUNCEMENTS", 988765608172736542))
    off_topic_0 = 291284109232308226
    off_topic_1 = 463035241142026251
    off_topic_2 = 463035268514185226
    voice_chat_0 = 412357430186344448
    voice_chat_1 = 799647045886541885


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
    # Override seasonal locks: 1 (January) to 12 (December)
    month_override = int(environ["MONTH_OVERRIDE"]) if "MONTH_OVERRIDE" in environ else None


class Colours:
    blue = 0x0279FD
    twitter_blue = 0x1DA1F2
    bright_green = 0x01D277
    dark_green = 0x1F8B4C
    orange = 0xE67E22
    pink = 0xCF84E0
    purple = 0xB734EB
    soft_green = 0x68C290
    soft_orange = 0xF9CB54
    soft_red = 0xCD6D6D
    yellow = 0xF9F586
    python_blue = 0x4B8BBE
    python_yellow = 0xFFD43B
    grass_green = 0x66FF00
    gold = 0xE6C200


class Emojis(NamedTuple):
    check_mark = "\u2705"
    envelope = "\U0001F4E8"
    trashcan = environ.get("TRASHCAN_EMOJI", "<:trashcan:637136429717389331>")
    star = "\u2B50"
    christmas_tree = "\U0001F384"


class Roles(NamedTuple):
    admins = int(environ.get("ROLE_ADMINS", 267628507062992896))
    code_jam_event_team = int(environ.get("ROLE_CODE_JAM_EVENT_TEAM", 787816728474288181))
    events_lead = int(environ.get("ROLE_EVENTS_LEAD", 778361735739998228))
    event_runner = int(environ.get("EVENT_RUNNER", 940911658799333408))
    summer_aoc = int(environ.get("ROLE_SUMMER_AOC", 988801794668908655))
    code_jam_participants = int(environ.get("CODE_JAM_PARTICIPANTS", 991678713093705781))
    helpers = int(environ.get("ROLE_HELPERS", 267630620367257601))
    aoc_completionist = int(environ.get("AOC_COMPLETIONIST_ROLE_ID", 916691790181056532))


class RedisConfig(NamedTuple):
    host = environ.get("REDIS_HOST", "redis.default.svc.cluster.local")
    port = environ.get("REDIS_PORT", 6379)
    password = environ.get("REDIS_PASSWORD")
    use_fakeredis = environ.get("USE_FAKEREDIS", "false").lower() == "true"


class Month(enum.IntEnum):
    JANUARY = 1
    FEBRUARY = 2
    MARCH = 3
    APRIL = 4
    MAY = 5
    JUNE = 6
    JULY = 7
    AUGUST = 8
    SEPTEMBER = 9
    OCTOBER = 10
    NOVEMBER = 11
    DECEMBER = 12

    def __str__(self) -> str:
        return self.name.title()


# If a month override was configured, check that it's a valid Month
# Prevents delaying an exception after the bot starts
if Client.month_override is not None:
    Month(Client.month_override)


# Whitelisted channels
WHITELISTED_CHANNELS = (
    Channels.bot_commands,
    Channels.sir_lancebot_playground,
    Channels.off_topic_0,
    Channels.off_topic_1,
    Channels.off_topic_2,
    Channels.voice_chat_0,
    Channels.voice_chat_1,
)

# Bot replies
ERROR_REPLIES = [
    "Please don't do that.",
    "You have to stop.",
    "Do you mind?",
    "In the future, don't do that.",
    "That was a mistake.",
    "You blew it.",
    "You're bad at computers.",
    "Are you trying to kill me?",
    "Noooooo!!",
    "I can't believe you've done this",
]

NEGATIVE_REPLIES = [
    "Noooooo!!",
    "Nope.",
    "I'm sorry Dave, I'm afraid I can't do that.",
    "I don't think so.",
    "Not gonna happen.",
    "Out of the question.",
    "Huh? No.",
    "Nah.",
    "Naw.",
    "Not likely.",
    "No way, José.",
    "Not in a million years.",
    "Fat chance.",
    "Certainly not.",
    "NEGATORY.",
    "Nuh-uh.",
    "Not in my house!",
]

POSITIVE_REPLIES = [
    "Yep.",
    "Absolutely!",
    "Can do!",
    "Affirmative!",
    "Yeah okay.",
    "Sure.",
    "Sure thing!",
    "You're the boss!",
    "Okay.",
    "No problem.",
    "I got you.",
    "Alright.",
    "You got it!",
    "ROGER THAT",
    "Of course!",
    "Aye aye, cap'n!",
    "I'll allow it.",
]
