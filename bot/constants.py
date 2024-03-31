import dataclasses
import enum
import logging
from datetime import UTC, datetime
from os import environ

from pydantic_settings import BaseSettings

log = logging.getLogger(__name__)


class EnvConfig(
    BaseSettings,
    env_file=".env",
    env_file_encoding="utf-8",
    env_nested_delimiter="__",
    extra="ignore",
):
    """Our default configuration for models that should load from .env files."""


@dataclasses.dataclass
class AdventOfCodeLeaderboard:
    """Config required for a since AoC leaderboard."""

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


class _AdventOfCode(EnvConfig, env_prefix="AOC_"):
    @staticmethod
    def _parse_aoc_leaderboard_env() -> dict[str, AdventOfCodeLeaderboard]:
        """
        Parse the environment variable containing leaderboard information.

        A leaderboard should be specified in the format `id,session,join_code`,
        without the backticks. If more than one leaderboard needs to be added to
        the constant, separate the individual leaderboards with `::`.

        Example ENV: `id1,session1,join_code1::id2,session2,join_code2`
        """
        raw_leaderboards = environ.get("AOC_RAW_LEADERBOARDS", "")
        if not raw_leaderboards:
            return {}

        leaderboards = {}
        for leaderboard in raw_leaderboards.split("::"):
            leaderboard_id, session, join_code = leaderboard.split(",")
            leaderboards[leaderboard_id] = AdventOfCodeLeaderboard(leaderboard_id, session, join_code)

        return leaderboards
    # Information for the several leaderboards we have
    leaderboards: dict[str, AdventOfCodeLeaderboard] = _parse_aoc_leaderboard_env()

    staff_leaderboard_id: str | None = None
    fallback_session: str | None = None

    ignored_days: tuple[int, ...] | None = None
    leaderboard_displayed_members: int = 10
    leaderboard_cache_expiry_seconds: int = 1800
    max_day_and_star_results: int = 15
    year: int = datetime.now(tz=UTC).year


AdventOfCode = _AdventOfCode()


class _Channels(EnvConfig, env_prefix="CHANNEL_"):
    advent_of_code: int = 897932085766004786
    advent_of_code_commands: int = 897932607545823342
    bot_commands: int = 267659945086812160
    devlog: int = 622895325144940554
    code_jam_planning: int = 490217981872177157
    summer_aoc_main: int = 988979042847957042
    summer_aoc_discussion: int = 996438901331861554
    sir_lancebot_playground: int = 607247579608121354
    summer_code_jam_announcements: int = 988765608172736542
    off_topic_0: int = 291284109232308226
    off_topic_1: int = 463035241142026251
    off_topic_2: int = 463035268514185226
    voice_chat_0: int = 412357430186344448
    voice_chat_1: int = 799647045886541885
    roles: int = 851270062434156586


Channels = _Channels()


class _Categories(EnvConfig, env_prefix="CATEGORY_"):
    summer_code_jam: int = 987738098525937745


Categories = _Categories()


class Month(enum.IntEnum):
    """
    Enum lookup between Months & month numbers.

    Can bre replaced with the below when upgrading to 3.12
    https://docs.python.org/3/library/calendar.html#calendar.Month
    """

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


class _Bot(EnvConfig, env_prefix="BOT_"):
    name: str = "Sir Robin"
    guild: int = 267624335836053506
    prefix: str = "&"
    token: str
    debug: bool = True
    trace_logging: bool = False
    in_ci: bool = False
    github_bot_repo: str = "https://github.com/python-discord/sir-robin"
    # Override seasonal locks: 1 (January) to 12 (December)
    month_override: Month | None = None
    sentry_dsn: str = ""


Bot = _Bot()


class _Codejam(EnvConfig, env_prefix="CODE_JAM_"):
    api: str = "http://code-jam-management.default.svc.cluster.local:8000"
    api_key: str = "badbot13m0n8f570f942013fc818f234916ca531"


Codejam = _Codejam()


class _Emojis(EnvConfig, env_prefix="EMOJI_"):
    check_mark: str = "\u2705"
    envelope: str = "\U0001F4E8"
    trashcan: str = "<:trashcan:637136429717389331>"
    star: str = "\u2B50"
    christmas_tree: str = "\U0001F384"
    team_tuple: str = "<:team_tuple:1224089419003334768>"
    team_list: str = "<:team_list:1224089544257962134>"
    team_dict: str = "<:team_dict:1224089495373353021>"


Emojis = _Emojis()


class _Roles(EnvConfig, env_prefix="ROLE_"):
    admins: int = 267628507062992896
    advent_of_code: int = 518565788744024082
    code_jam_event_team: int = 787816728474288181
    events_lead: int = 778361735739998228
    event_runner: int = 940911658799333408
    summer_aoc: int = 988801794668908655
    code_jam_participants: int = 991678713093705781
    helpers: int = 267630620367257601
    aoc_completionist: int = 1191547731873894440
    bots: int = 277546923144249364

    team_list: int = 1222691191582097418
    team_dict: int = 1222691368653033652
    team_tuple: int = 1222691399246286888


Roles = _Roles()


class _RedisConfig(EnvConfig, env_prefix="REDIS_"):
    host: str = "redis.default.svc.cluster.local"
    port: int = 6379
    password: str | None = None
    use_fakeredis: bool = False


RedisConfig = _RedisConfig()


class Colours:
    """Colour hex values commonly used throughout the bot."""

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


# Git SHA for Sentry
GIT_SHA = environ.get("GIT_SHA", "development")


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
ERROR_REPLIES = (
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
)

NEGATIVE_REPLIES = (
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
)

POSITIVE_REPLIES = (
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
)
