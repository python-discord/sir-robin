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


class PydisGames(commands.Cog):
    """Facilitate our glorious games."""
    team_adjectives = types.MappingProxyType({
        Team.LIST: ['noble', 'organized', 'orderly', 'chivalrous', 'valiant'],
        Team.DICT: ['wise', 'knowledgeable', 'powerful', ],
        Team.TUPLE: ['resilient', 'strong', 'steadfast', 'resourceful', ],
    })

    # RedisCache[Team, int]
    points = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot
        self.team_roles: dict[Team, discord.Role] | None = None

    async def _refresh_roles(self) -> None:
        self.team_roles = {
            role: self.bot.get_guild(267624335836053506).get_role(role_id)
            for role, role_id in
            [
                (Team.LIST, 1),
                (Team.DICT, 2),
                (Team.TUPLE, 3),
            ]
        }

    async def award_points(self, team: Team, points: int) -> None:
        await self.points.increment(team, points)

    @commands.group(name="games")
    async def games_command_group(self, ctx: commands.Context) -> None:
        pass

    @games_command_group.command
    async def join(self, ctx: commands.Context) -> None:
        if not self.team_roles:
            await self._refresh_roles()

        team_with_fewest_members: Team = min(
            self.team_roles.keys(), key=lambda role: len(role.members)
        )
        role_with_fewest_members: discord.Role = self.team_roles[team_with_fewest_members]
        await ctx.author.add_roles(role_with_fewest_members)

        adjective: str = random.choice(self.team_adjectives[team_with_fewest_members])
        await ctx.send(f"{ctx.author.mention} you are very {adjective}. "
                       f"You have been assigned {role_with_fewest_members.mention}!")

    @games_command_group.command(alias=('score', 'points'))
    async def scores(self, ctx: commands.Context):
        current_points: list[str, int] = sorted(await self.points.items(), key=lambda t: t[1])
        team_messages = '\n'.join(
            f"Team {team_name.capitalize()}: {points}\n"
            for team_name, points in current_points
        )
        message = f"The current points are:\n{team_messages}"
        await ctx.send(message)


async def setup(bot: SirRobin) -> None:
    """Load the BlurpleFormatter cog."""
    await bot.add_cog(PydisGames(bot))

