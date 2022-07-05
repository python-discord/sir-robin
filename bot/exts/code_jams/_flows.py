from datetime import datetime

import discord
from discord.ext import commands
from discord import Embed, Member

from bot.bot import SirRobin
from bot.exts.code_jams import _creation_utils
from bot.exts.code_jams._views import JamTeamInfoConfirmation
from bot.constants import Channels

TEAM_LEADERS_COLOUR = 0x11806a


async def creation_flow(
        ctx: commands.Context,
        teams: dict[str: list[dict[str: Member, str: bool]]],
        bot: SirRobin
) -> None:
    team_leaders = await ctx.guild.create_role(name="Code Jam Team Leaders", colour=TEAM_LEADERS_COLOUR)
    await _creation_utils.create_team_leader_channel(ctx.guild, team_leaders)
    jam_api_format = {"name": f"Summer Code Jam {datetime.now().year}", "ongoing": True, "teams": []}
    for team_name, team_members in teams.items():
        team_role = await _creation_utils.create_team_role(
            ctx.guild,
            team_name,
            team_members,
            team_leaders
        )
        team_channel_id = await _creation_utils.create_team_channel(ctx.guild, team_name, team_role)
        jam_api_format["teams"].append(
            {
                "name": team_name,
                "users": [
                    {"user_id": entry["member"].id, "is_leader": entry["is_leader"]} for entry in team_members
                ],
                "discord_role_id": team_role.id,
                "discord_channel_id": team_channel_id
            }
        )
    await bot.code_jam_mgmt_api.post("codejams", json=jam_api_format)
    success_embed = Embed(
        title=f"Successfully created Code Jam with {len(teams)} teams",
        colour=discord.Colour.green(),
        description="Would you like send out the team announcement?"
    )
    success_embed.set_footer(text="Code Jam team generation")
    team_info_view = JamTeamInfoConfirmation(bot, ctx.guild, ctx.author)
    await ctx.send(
        embed=success_embed,
        view=team_info_view
    )


async def deletion_flow(category_channels: dict[discord.CategoryChannel: list[discord.TextChannel]],
                        roles: list[discord.Role]) -> None:
    for category, channels in category_channels.items():
        for channel in channels:
            await channel.delete(reason="Code jam ended.")
        await category.delete(reason="Code jam ended.")
    for role in roles:
        await role.delete(reason="Code Jam ended.")
