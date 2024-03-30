import asyncio
import enum
import random
import types
from collections import namedtuple, Counter
from typing import Literal

import arrow
import discord
from async_rediscache import RedisCache
from discord.ext import commands, tasks
from pydis_core.utils.logging import get_logger

from bot import constants
from bot.bot import SirRobin

logger = get_logger(__name__)


team_info = namedtuple("team_info", ("name", "emoji"))


class Team(enum.Enum):
    """The three teams for Python Discord Games 2024."""

    LIST = team_info("list", constants.Emojis.team_list)
    DICT = team_info("dict", constants.Emojis.team_dict)
    TUPLE = team_info("tuple", constants.Emojis.team_tuple)


TEAM_ADJECTIVES = types.MappingProxyType({
    Team.LIST: ["noble", "organized", "orderly", "chivalrous", "valiant"],
    Team.DICT: ["wise", "knowledgeable", "powerful"],
    Team.TUPLE: ["resilient", "strong", "steadfast", "resourceful"],
})

# Minimum and maximum time to add team reaction, in seconds.
REACTION_INTERVALS_SECONDS: types.MappingProxyType[Literal["team", "super"], tuple[int, int]] = types.MappingProxyType({
    "team": (30, 120),
    "super": (20 * 60, 40 * 60)
})

# Channels where the game runs.
ALLOWED_CHANNELS = (
    constants.Channels.off_topic_0,
    constants.Channels.off_topic_1,
    constants.Channels.off_topic_2,
)

# Time for a reaction to be up, in seconds.
EVENT_UP_TIME = 5
QUACKSTACK_URL = "https://quackstack.pythondiscord.com/duck"


class PydisGames(commands.Cog):
    """Facilitate our glorious games."""

    # TODO limit the cog commands to bot-commands

    # RedisCache[Team, int]
    points = RedisCache()

    # RedisCache[Literal["team", "super"], float timestamp]
    target_times = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot
        self.guild = self.bot.get_guild(constants.Bot.guild)
        self.team_roles: dict[Team, discord.Role] = {}

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

        team_scores = await self.points.items()
        for role in self.team_roles:
            if role.value.name not in team_scores:
                await self.points.set(role.value.name, 0)

        times = await self.target_times.items()
        for reaction_type in REACTION_INTERVALS_SECONDS:
            if reaction_type not in times:
                await self.set_time(reaction_type)

        self.super_game.start()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """Add a reaction if it's time and the message is in the right channel, then remove it after a few seconds."""
        # TODO does this need a lock to prevent race conditions?
        if msg.channel.id not in ALLOWED_CHANNELS:
            return

        reaction_time: float = await self.target_times.get("team")
        if arrow.utcnow() < arrow.Arrow.fromtimestamp(reaction_time):
            return
        await self.set_time("team")

        self.team_game_message_id = msg.id
        self.chosen_team = random.choice(list(Team))
        logger.info(f"Starting game in {msg.channel.name} for team {self.chosen_team}")
        await msg.add_reaction(self.chosen_team.value.emoji)

        await asyncio.sleep(EVENT_UP_TIME)

        await msg.clear_reaction(self.chosen_team.value.emoji)
        self.team_game_message_id = self.chosen_team = None
        self.team_game_users_already_reacted.clear()

    async def handle_team_game_reaction(self, reaction: discord.Reaction, user: discord.Member) -> None:
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
            self.super_game_users_reacted.add(user)

    @tasks.loop(minutes=5)
    async def super_game(self):
        if random.random() < .25:
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
            duck_image_url = response.headers['Location']

        embed = discord.Embed(
            title="Quack!",
            description="Every gamer react to this message before time runs out for extra points!"
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

    def get_team(self, member: discord.Member) -> Team | None:
        """Return the member's team, if they have one."""
        for team, role in self.team_roles.items():
            if role in member.roles:
                return team
        return None

    async def set_time(self, reaction_type: Literal["team", "super"]) -> None:
        """Set the time after which a reaction of the appropriate time can be added."""
        interval = REACTION_INTERVALS_SECONDS[reaction_type]
        relative_seconds_to_next_reaction = random.randint(interval[0], interval[1])
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
            f"You seem to be extremely {adjective}. You shall be assigned to... {role_with_fewest_members.mention}!"
        )

    @games_command_group.command(aliases=("score", "points", "leaderboard", "lb"))
    async def scores(self, ctx: commands.Context) -> None:
        """The current leaderboard of points for each team."""
        current_points: list = sorted(await self.points.items(), key=lambda t: t[1])
        team_scores = "\n".join(
            f"{Team[team_name.upper()].value.emoji} **Team {team_name.capitalize()}**: {points}\n"
            for team_name, points in current_points
        )
        embed = discord.Embed(title="Current team points", description=team_scores, color=discord.Colour.blurple())
        await ctx.send(embed=embed)


async def setup(bot: SirRobin) -> None:
    """Load the PydisGames cog."""
    await bot.add_cog(PydisGames(bot))
