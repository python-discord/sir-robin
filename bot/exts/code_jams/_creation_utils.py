import typing as t

import discord
from botcore.utils.logging import get_logger

from bot.constants import Channels, Roles

log = get_logger(__name__)


def _get_overwrites(
        guild: discord.Guild,
        team_role: discord.Role
) -> dict[t.Union[discord.Member, discord.Role], discord.PermissionOverwrite]:
    """Get code jam team channels permission overwrites."""
    return {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.get_role(Roles.code_jam_event_team): discord.PermissionOverwrite(read_messages=True),
        team_role: discord.PermissionOverwrite(read_messages=True)
    }


async def create_team_role(
        guild: discord.Guild,
        team_name: str,
        members: list[tuple[discord.Member, bool]],
        team_leaders: discord.Role
) -> discord.Role:
    await _add_team_leader_roles(members, team_leaders)
    team_role = await guild.create_role(name=team_name, reason="Code Jam team creation")
    for member, _ in members:
        await member.add_roles(team_role)
    return team_role


async def create_team_channel(
        guild: discord.Guild,
        team_name: str,
        team_role: discord.Role

) -> int:
    """Create the team's text channel."""

    # Get permission overwrites and category
    team_channel_overwrites = _get_overwrites(guild, team_role)
    code_jam_category = guild.get_channel(Channels.summer_code_jam)

    # Create a text channel for the team
    created_channel = await code_jam_category.create_text_channel(
        team_name,
        overwrites=team_channel_overwrites,
    )
    return created_channel.id


async def create_team_leader_channel(guild: discord.Guild, team_leaders: discord.Role) -> None:
    """Create the Team Leader Chat channel for the Code Jam team leaders."""
    category: discord.CategoryChannel = guild.get_channel(Channels.summer_code_jam)

    team_leaders_chat = await category.create_text_channel(
        name="team-leaders-chat",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            team_leaders: discord.PermissionOverwrite(read_messages=True)
        }
    )

    await _send_status_update(guild, f"Created {team_leaders_chat.mention} in the {category} category.")


async def _send_status_update(guild: discord.Guild, message: str) -> None:
    """Inform the events lead with a status update when the command is ran."""
    channel: discord.TextChannel = guild.get_channel(Channels.code_jam_planning)

    await channel.send(f"<@&{Roles.events_lead}>\n\n{message}")


async def _add_team_leader_roles(members: list[tuple[discord.Member, bool]], team_leaders: discord.Role) -> None:
    """Assign the team leader role to the team leaders."""
    for member, is_leader in members:
        if is_leader:
            await member.add_roles(team_leaders)
