import enum
import random
import types
from collections import namedtuple

import discord
from async_rediscache import RedisCache
from discord.ext import commands
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


class PydisGames(commands.Cog):
    """Facilitate our glorious games."""

    # RedisCache[Team, int]
    points = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot
        self.team_roles: dict[Team, discord.Role] = {}

    async def cog_load(self) -> None:
        """Set the team roles and initial scores. Don't load the cog if any roles are missing."""
        await self.bot.wait_until_guild_available()

        self.team_roles: dict[Team, discord.Role] = {
            role: self.bot.get_guild(constants.Bot.guild).get_role(role_id)
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

    async def award_points(self, team: Team, points: int) -> None:
        """Increment points for a team."""
        await self.points.increment(team, points)

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
