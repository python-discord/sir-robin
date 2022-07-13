from datetime import datetime
from urllib.parse import quote as quote_url

import discord
from botcore.site_api import ResponseCodeError
from botcore.utils.logging import get_logger
from discord import Embed, Member
from discord.ext import commands

from bot.bot import SirRobin
from bot.exts.code_jams import _creation_utils
from bot.exts.code_jams._views import JamTeamInfoConfirmation

TEAM_LEADERS_COLOUR = 0x11806a
TEAM_LEADER_ROLE_NAME = "Code Jam Team Leaders"

log = get_logger(__name__)


async def creation_flow(
        ctx: commands.Context,
        teams: dict[str: list[dict[str: Member, str: bool]]],
        bot: SirRobin
) -> None:
    """
    The Code Jam Team and Role creation flow.

    This "flow" will first create the role for the CJ Team leaders, and the channel.
    Then it'll create the team roles first, then the team channels.
    After that all the information regarding the teams will be uploaded to
    the Code Jam Management System, via an HTTP request.
    Finally, a view of Team Announcement will be sent.
    """
    team_leaders = await ctx.guild.create_role(name=TEAM_LEADER_ROLE_NAME, colour=TEAM_LEADERS_COLOUR)
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


async def deletion_flow(
        category_channels: dict[discord.CategoryChannel: list[discord.TextChannel]],
        roles: list[discord.Role]
) -> None:
    """
    The Code Jam Team and Role deletion flow.

    The "flow" will delete the channels in each category, and the category itself.
    Then it'll delete all the Team roles, leaving the CJ Leaders related channel, and Roles intact.
    """
    for category, channels in category_channels.items():
        for channel in channels:
            await channel.delete(reason="Code jam ended.")
        await category.delete(reason="Code jam ended.")
    for role in roles:
        await role.delete(reason="Code Jam ended.")


async def move_flow(
        bot: SirRobin,
        new_team_name: str,
        ctx: commands.Context,
        member: discord.Member
) -> None:
    """Move participant from one team to another by issuing an HTTP request to the Code Jam Management system."""
    # Query the current team of the member
    try:
        team = await bot.code_jam_mgmt_api.get(f"users/{member.id}/current_team",
                                               raise_for_status=True)
    except ResponseCodeError as err:
        if err.response.status == 404:
            await ctx.send(":x: It seems like the user is not a participant!")
        else:
            await ctx.send("Something went wrong while processing the request! We have notified the team!")
            log.error(err.response)
        return

    # Query the team the user has to be moved to
    try:
        team_to_move_in = await bot.code_jam_mgmt_api.get(
            "teams/find",
            params={"name": new_team_name, "jam_id": team["team"]["jam_id"]},
            raise_for_status=True
        )
    except ResponseCodeError as err:
        if err.response.status == 404:
            await ctx.send(f":x: Team `{new_team_name}` does not exist in the current jam!")
        else:
            await ctx.send("Something went wrong while processing the request! We have notified the team!")
            log.error(f"Something went wrong with processing the request! {err}")
        return

    # Check if the user's current team and the team they want to move them to is not the same
    if team_to_move_in["name"] == team["team"]["name"]:
        await ctx.send(f":x: user {member.mention} is already in {team_to_move_in['name']}")
        return

    # Remove the member from their current team.
    try:
        await bot.code_jam_mgmt_api.delete(
            f"teams/{quote_url(str(team['team']['id']))}/users/{quote_url(str(team['user_id']))}",
            raise_for_status=True
        )
    except ResponseCodeError as err:
        if err.response.status == 404:
            await ctx.send(":x: Team or user could not be found!")
        elif err.response.status == 400:
            await ctx.send(":x: The member given is not part of the team! (Might have been removed already)")
        else:
            await ctx.send("Something went wrong while processing the request! We have notified the team!")
            log.error(f"Something went wrong with processing the request! {err}")
        return

    # Actually remove the role to modify the permissions.
    team_role = ctx.guild.get_role(team["team"]["discord_role_id"])
    await member.remove_roles(team_role)

    # Decide whether the member should be a team leader in their new team.
    is_leader = False
    members = team["team"]["users"]
    for memb in members:
        if memb["user_id"] == member.id and memb["is_leader"]:
            is_leader = True

    # Add the user to the new team in the database.
    try:
        await bot.code_jam_mgmt_api.post(
            f"teams/{team_to_move_in['id']}/users/{member.id}",
            params={"is_leader": str(is_leader)},
            raise_for_status=True
        )
    except ResponseCodeError as err:
        if err.response.status == 404:
            await ctx.send(":x: Team or user could not be found.")
        elif err.response.status == 400:
            await ctx.send(f":x: user {member.mention} is already in {team_to_move_in['name']}")
        else:
            await ctx.send(
                "Something went wrong while processing the request! We have notified the team!"
            )
            log.error(f"Something went wrong with processing the request! {err}")
        return

    await member.add_roles(ctx.guild.get_role(team_to_move_in['discord_role_id']))

    await ctx.send(
        f"Success! Participant {member.mention} has been moved "
        f"from {team['team']['name']} to {team_to_move_in['name']}"
    )


async def remove_flow(bot: SirRobin, member: discord.Member, ctx: commands.Context) -> None:
    """Remove the participant from their team. Does not remove the participants or leader roles."""
    try:
        team = await bot.code_jam_mgmt_api.get(
            f"users/{member.id}/current_team",
            raise_for_status=True
        )
    except ResponseCodeError as err:
        if err.response.status == 404:
            await ctx.send(":x: It seems like the user is not a participant!")
        else:
            await ctx.send("Something went wrong while processing the request! We have notified the team!")
            log.error(err.response)
        return

    try:
        await bot.code_jam_mgmt_api.delete(
            f"teams/{quote_url(str(team['team']['id']))}/users/{quote_url(str(team['user_id']))}",
            raise_for_status=True
        )
    except ResponseCodeError as err:
        if err.response.status == 404:
            await ctx.send(":x: Team or user could not be found!")
        elif err.response.status == 400:
            await ctx.send(":x: The member given is not part of the team! (Might have been removed already)")
        else:
            await ctx.send("Something went wrong while processing the request! We have notified the team!")
            log.error(err.response)
        return

    team_role = ctx.guild.get_role(team["team"]["discord_role_id"])
    await member.remove_roles(team_role)
    for role in member.roles:
        if role.name == TEAM_LEADER_ROLE_NAME:
            await member.remove_roles(role)
    await ctx.send(f"Successfully removed {member.mention} from team {team['team']['name']}")
