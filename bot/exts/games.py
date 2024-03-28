import asyncio
import traceback
import enum
import types
import random

import discord
from discord.ext import commands
from pydis_core.utils.logging import get_logger
from pydis_core.utils.paste_service import PasteFile, PasteTooLongError, PasteUploadError, send_to_paste_service
from pydis_core.utils.regex import FORMATTED_CODE_REGEX
from async_rediscache import RedisCache

from bot.bot import SirRobin
from bot import constants

logger = get_logger()


class Team(enum.StrEnum):
    LIST = 'list'
    DICT = 'dict'
    TUPLE = 'tuple'

TEAM_ADJECTIVES = types.MappingProxyType({
    Team.LIST: ['noble', 'organized', 'orderly', 'chivalrous', 'valiant'],
    Team.DICT: ['wise', 'knowledgeable', 'powerful'],
    Team.TUPLE: ['resilient', 'strong', 'steadfast', 'resourceful'],
})


class PydisGames(commands.Cog):
    """Facilitate our glorious games."""
    # RedisCache[Team, int]
    points = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot
        self.team_roles: dict[Team, discord.Role] = {
            role: self.bot.get_guild(constants.Bot.guild).get_role(role_id)
            for role, role_id in
            [
                (Team.LIST, constants.Roles.team_list),
                (Team.DICT, constants.Roles.team_dict),
                (Team.TUPLE, constants.Roles.team_tuple),
            ]
        }

    async def award_points(self, team: Team, points: int):
        await self.points.increment(team, points)

    @commands.group(name="games")
    async def games_command_group(self, ctx: commands.Context):
        pass

    @games_command_group.command(aliases=('assign',))
    async def join(self, ctx: commands.Context):
        """Let the sorting hat decide the team you shall join!"""
        # FIXME: Check that the user isn't already assigned to a team.

        team_with_fewest_members: Team = min(
            self.team_roles.keys(), key=lambda role: len(self.team_roles[role].members)
        )
        role_with_fewest_members: discord.Role = self.team_roles[team_with_fewest_members]

        await ctx.author.add_roles(role_with_fewest_members)

        adjective: str = random.choice(TEAM_ADJECTIVES[team_with_fewest_members])
        await ctx.send(f"{ctx.author.mention}, you seem to be extremely {adjective}. "
                       f"You shall be assigned to... {role_with_fewest_members.mention}!")

    @games_command_group.command(aliases=('score', 'points', 'leaderboard', 'lb'))
    async def scores(self, ctx: commands.Context):
        """The current leaderboard of points for each team."""
        current_points: list = sorted(await self.points.items(), key=lambda t: t[1])
        team_messages = '\n'.join(
            f"Team {team_name.capitalize()}: {points}\n"
            for team_name, points in current_points
        )
        message = f"The current points are:\n{team_messages}"
        await ctx.send(message)


async def setup(bot: SirRobin) -> None:
    """Load the PydisGames cog."""
    await bot.add_cog(PydisGames(bot))
