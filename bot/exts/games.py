import asyncio
import contextlib
import enum
import random
import textwrap
import types
from collections import Counter
from typing import Literal, NamedTuple

import arrow
import discord
import discord.errors
from async_rediscache import RedisCache
from discord.ext import commands, tasks
from discord.ext.commands import BadArgument
from pydis_core.utils.logging import get_logger

from bot import constants
from bot.bot import SirRobin
from bot.utils.decorators import in_whitelist

logger = get_logger(__name__)
GameType = Literal["team", "super"]


class TeamInfo(NamedTuple):
    """Tuple containing the info on a team."""

    name: str
    emoji: str


class Team(enum.Enum):
    """The three teams for Python Discord Games 2024."""

    LIST = TeamInfo("list", constants.Emojis.team_list)
    DICT = TeamInfo("dict", constants.Emojis.team_dict)
    TUPLE = TeamInfo("tuple", constants.Emojis.team_tuple)


TEAM_ADJECTIVES = types.MappingProxyType({
    Team.LIST: ["noble", "organized", "orderly", "chivalrous", "valiant"],
    Team.DICT: ["wise", "knowledgeable", "powerful"],
    Team.TUPLE: ["resilient", "strong", "steadfast", "resourceful"],
})

# The default settings to initialize the cache with.
DEFAULT_SETTINGS: types.MappingProxyType[str, int | float] = types.MappingProxyType({
    "reaction_min": 30, "reaction_max": 120, "ducky_probability": 0.25, "game_uptime": 15
})

# Channels where the game runs.
ALLOWED_CHANNELS = (
    constants.Channels.off_topic_0,
    constants.Channels.off_topic_1,
    constants.Channels.off_topic_2,
)
# Channels where the game commands can be run.
ALLOWED_COMMAND_CHANNELS = (constants.Channels.bot_commands,)

# Roles allowed to use the management commands.
ELEVATED_ROLES = (constants.Roles.admins, constants.Roles.moderation_team, constants.Roles.events_lead)

QUACKSTACK_URL = "https://quackstack.pythondiscord.com/duck"


class PydisGames(commands.Cog):
    """Facilitate our glorious games."""

    # RedisCache[Team, int]
    points = RedisCache()

    # RedisCache[GameType, float timestamp]
    target_times = RedisCache()

    # RedisCache["value", bool]
    is_on = RedisCache()

    # RedisCache[str, int | float]
    game_settings = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot
        self.guild = self.bot.get_guild(constants.Bot.guild)
        self.team_roles: dict[Team, discord.Role] = {}

        self.event_uptime: int = 15

        self.team_game_message_id = None
        self.team_game_users_already_reacted: set[int] = set()
        self.chosen_team = None

        self.super_game_message_id = None
        self.super_game_users_reacted: set[discord.Member] = set()

    async def cog_load(self) -> None:
        """Set the team roles and initialize the cache. Don't load the cog if any roles are missing."""
        await self.bot.wait_until_guild_available()

        self.team_roles: dict[Team, discord.Role] = {
            role: self.guild.get_role(role_id)
            for role, role_id in
            [
                (Team.LIST, constants.Roles.team_list),
                (Team.DICT, constants.Roles.team_dict),
                (Team.TUPLE, constants.Roles.team_tuple),
            ]
        }

        if any(role is None for role in self.team_roles.values()):
            raise ValueError("One or more team roles are missing.")

        team_scores = await self.points.to_dict()
        for role in self.team_roles:
            if role.value.name not in team_scores:
                logger.debug(f"Initializing {role} with score 0.")
                await self.points.set(role.value.name, 0)

        settings = await self.game_settings.to_dict()
        for setting_name, value in DEFAULT_SETTINGS.items():
            if setting_name not in settings:
                logger.debug(f"The setting {setting_name} wasn't found, setting the default.")
                await self.game_settings.set(setting_name, value)

        times = await self.target_times.items()
        if "team" not in times:
            await self.set_reaction_time("team")

        self.event_uptime = await self.game_settings.get("game_uptime")
        self.super_game.start()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """Add a reaction if it's time and the message is in the right channel, then remove it after a few seconds."""
        if (
            self.team_game_message_id is not None
            or msg.channel.id not in ALLOWED_CHANNELS
            or msg.author.bot
            or not (await self.is_on.get("value", False))
        ):
            return

        reaction_time: float = await self.target_times.get("team")
        if arrow.utcnow() < arrow.Arrow.fromtimestamp(reaction_time):
            return
        await self.set_reaction_time("team")

        self.team_game_message_id = msg.id
        self.chosen_team = await self.weighted_random_team()
        logger.info(f"Starting game in {msg.channel.name} for team {self.chosen_team}")
        await msg.add_reaction(self.chosen_team.value.emoji)

        await asyncio.sleep(self.event_uptime)

        # If the message was deleted in the meantime, the
        # reaction is gone either way. Continue with cleanup.
        with contextlib.suppress(discord.errors.NotFound):
            await msg.clear_reaction(self.chosen_team.value.emoji)
        self.team_game_message_id = self.chosen_team = None
        self.team_game_users_already_reacted.clear()

    async def handle_team_game_reaction(self, reaction: discord.Reaction, user: discord.Member) -> None:
        """Award points depending on the user's team."""
        if user.id in self.team_game_users_already_reacted:
            return

        member_team = self.get_team(user)
        if not member_team:
            return

        self.team_game_users_already_reacted.add(user.id)

        if member_team == self.chosen_team:
            await self.award_points(member_team, 1)
        else:
            await self.award_points(member_team, -1)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member) -> None:
        """Update score for the user's team."""
        if reaction.message.id == self.team_game_message_id and self.team_game_message_id is not None:
            await self.handle_team_game_reaction(reaction, user)
        elif reaction.message.id == self.super_game_message_id and self.super_game_message_id is not None:
            if not isinstance(reaction.emoji, str) and reaction.emoji.name.startswith("ducky_"):
                self.super_game_users_reacted.add(user)

    @tasks.loop(minutes=5)
    async def super_game(self) -> None:
        """The super game task. Send a ducky, wait for people to react, and tally the points at the end."""
        if not (await self.is_on.get("value", False)):
            return

        probability = await self.game_settings.get("ducky_probability")
        if random.random() > probability:
            # with a 25% chance every 5 minutes, the event should happen on average
            # three times an hour
            logger.info("Super game occurrence randomly skipped.")
            return

        channel = self.guild.get_channel(random.choice(ALLOWED_CHANNELS))
        logger.info(f"Starting a super game in {channel.name}")

        async with self.bot.http_session.get(QUACKSTACK_URL) as response:
            if response.status != 201:
                logger.error(f"Response to Quackstack returned code {response.status}")
                return
            duck_image_url = response.headers["Location"]

        embed = discord.Embed(
            title="Quack!",
            description="Every gamer react **with a ducky** to this message before time runs out for extra points!",
            color=discord.Colour.gold()
        )
        embed.set_image(url=duck_image_url)

        message = await channel.send(embed=embed)
        self.super_game_message_id = message.id
        await asyncio.sleep(15)

        team_counts = Counter(self.get_team(user) for user in self.super_game_users_reacted)
        team_counts.pop(None, None)
        self.super_game_users_reacted.clear()

        logger.debug(f"{team_counts = }")
        for team, count in team_counts.items():
            await self.award_points(team, count * 5)

        embed.description = "Time's up! Hope you reacted in time."
        await message.edit(embed=embed)

    def get_team(self, member: discord.Member) -> Team | None:
        """Return the member's team, if they have one."""
        for team, role in self.team_roles.items():
            if role in member.roles:
                return team
        return None

    async def weighted_random_team(self) -> Team:
        """Randomly select the next chosen team weighted by current team points."""
        scores = await self.points.to_dict()
        teams: list[str] = list(scores.keys())
        inverse_points = [1 / (points or 1) for points in scores.values()]
        total_inverse_weights = sum(inverse_points)
        weights = [w / total_inverse_weights for w in inverse_points]

        logger.debug(f"{scores = }, {weights = }")

        team_selection = random.choices(teams, weights=weights, k=1)[0]
        return Team[team_selection.upper()]

    async def set_reaction_time(self, reaction_type: GameType) -> None:
        """Set the time after which a team reaction can be added."""
        reaction_min = await self.game_settings.get("reaction_min")
        reaction_max = await self.game_settings.get("reaction_max")
        relative_seconds_to_next_reaction = random.randint(reaction_min, reaction_max)
        next_reaction_timestamp = arrow.utcnow().shift(seconds=relative_seconds_to_next_reaction).timestamp()

        await self.target_times.set(reaction_type, next_reaction_timestamp)

    async def award_points(self, team: Team, points: int) -> None:
        """Increment points for a team."""
        await self.points.increment(team.value.name, points)

    @commands.group(name="games")
    async def games_command_group(self, ctx: commands.Context) -> None:
        """The games command group."""
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @games_command_group.command(aliases=("assign",))
    @in_whitelist(channels=ALLOWED_COMMAND_CHANNELS, redirect=ALLOWED_COMMAND_CHANNELS)
    async def join(self, ctx: commands.Context) -> None:
        """Let the sorting hat decide the team you shall join!"""
        if any(role in ctx.author.roles for role in self.team_roles.values()):
            await ctx.reply("You're already assigned to a team!")
            return

        team_with_fewest_members: Team = min(
            self.team_roles, key=lambda role: len(self.team_roles[role].members)
        )
        role_with_fewest_members: discord.Role = self.team_roles[team_with_fewest_members]

        await ctx.author.add_roles(role_with_fewest_members)

        adjective: str = random.choice(TEAM_ADJECTIVES[team_with_fewest_members])
        await ctx.reply(
            f"You seem to be extremely {adjective}. You shall be assigned to... {role_with_fewest_members.mention}!",
            allowed_mentions=discord.AllowedMentions(roles=False, replied_user=True),
        )

    @games_command_group.command(aliases=("score", "points", "leaderboard", "lb"))
    @in_whitelist(channels=ALLOWED_COMMAND_CHANNELS, redirect=ALLOWED_COMMAND_CHANNELS)
    async def scores(self, ctx: commands.Context) -> None:
        """The current leaderboard of points for each team."""
        current_points: list = sorted(await self.points.items(), key=lambda t: t[1], reverse=True)
        team_scores = "\n".join(
            f"{Team[team_name.upper()].value.emoji} **Team {team_name.capitalize()}**: {points}\n"
            for team_name, points in current_points
        )
        embed = discord.Embed(title="Current team points", description=team_scores, color=discord.Colour.blurple())
        await ctx.send(embed=embed)

    @games_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def on(self, ctx: commands.Context) -> None:
        """Turn on the games."""
        await self.is_on.set("value", True)
        await ctx.message.add_reaction("✅")

    @games_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def off(self, ctx: commands.Context) -> None:
        """Turn off the games."""
        await self.is_on.set("value", False)
        await ctx.message.add_reaction("✅")

    @games_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def set_interval(self, ctx: commands.Context, min_time: int, max_time: int) -> None:
        """Set the minimum and maximum number of seconds between team reactions."""
        if min_time > max_time:
            await ctx.send("The minimum interval can't be greater than the maximum.")
            return

        game_uptime = await self.game_settings.get("game_uptime")
        if min_time < game_uptime:
            await ctx.send(f"Min time can't be less than the game uptime, which is {game_uptime}")
            return

        logger.info(f"New game intervals set to {min_time}, {max_time} by {ctx.author.name}")

        await self.game_settings.set("reaction_min", min_time)
        await self.game_settings.set("reaction_max", max_time)
        await ctx.message.add_reaction("✅")

    @games_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def set_probability(self, ctx: commands.Context, probability: float) -> None:
        """
        Set the probability for the super ducky to be posted once every 5 minutes. Value is between 0 and 1.

        For example, with a 25% (0.25) chance every 5 minutes, the event should happen on average three times an hour.
        """
        if probability < 0 or probability > 1:
            raise BadArgument("Value must be between 0 and 1.")

        await self.game_settings.set("ducky_probability", probability)
        await ctx.message.add_reaction("✅")

    @games_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def set_uptime(self, ctx: commands.Context, uptime: int) -> None:
        """Set the number of seconds for which the team game runs."""
        if uptime <= 0:
            await ctx.send(f"Uptime must be greater than 0, but is {uptime}")
            return

        current_min = await self.game_settings.get("reaction_min")
        if uptime > current_min:
            await ctx.send(f"Uptime can't be greater than the minimum interval, which is {current_min}")
            return

        await self.game_settings.set("game_uptime", uptime)
        self.event_uptime = uptime
        logger.info(f"game_uptime set to {uptime}s by {ctx.author.name}")
        await ctx.message.add_reaction("✅")

    @games_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def status(self, ctx: commands.Context) -> None:
        """Get the state of the games."""
        is_on = await self.is_on.get("value", False)
        min_reaction_time = await self.game_settings.get("reaction_min")
        max_reaction_time = await self.game_settings.get("reaction_max")
        ducky_probability = await self.game_settings.get("ducky_probability")

        description = textwrap.dedent(f"""
            Is on: **{is_on}**
            Min time between team reactions: **{min_reaction_time}**
            Max time between team reactions: **{max_reaction_time}**
            Ducky probability: **{ducky_probability}**
        """)
        embed = discord.Embed(
            title="Games State",
            description=description,
            color=discord.Colour.blue()
        )
        await ctx.reply(embed=embed)


async def setup(bot: SirRobin) -> None:
    """Load the PydisGames cog."""
    await bot.add_cog(PydisGames(bot))
