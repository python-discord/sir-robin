import typing as t

import discord
from botcore.utils.logging import get_logger
from discord.ext import commands

from bot.constants import Channels, Roles
from bot.utils.exceptions import JamCategoryNameConflictError

log = get_logger(__name__)

MAX_CHANNELS = 50
CATEGORY_NAME = "Code Jam"


async def _create_category(guild: discord.Guild) -> discord.CategoryChannel:
    """Create a new code jam category and return it."""
    log.info("Creating a new code jam category.")

    category_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    category = await guild.create_category_channel(
        CATEGORY_NAME,
        overwrites=category_overwrites,
        reason="It's code jam time!"
    )

    await _send_status_update(
        guild, f"Created a new category with the ID {category.id} for this Code Jam's team channels."
    )

    return category


async def _get_category(guild: discord.Guild) -> discord.CategoryChannel:
    """
    Return a code jam category.

    If all categories are full or none exist, create a new category.
    If the main CJ category and the CJ Team's category has the same name
    it raises a `JamCategoryNameConflictError`
    """
    main_cj_category = guild.get_channel(Channels.summer_code_jam).name
    if main_cj_category == CATEGORY_NAME:
        raise JamCategoryNameConflictError()

    for category in guild.categories:
        if category.name == CATEGORY_NAME and len(category.channels) < MAX_CHANNELS:
            return category

    return await _create_category(guild)


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
        members: list[dict[str: discord.Member, str: bool]],
        team_leaders: discord.Role
) -> discord.Role:
    """Create the team's role."""
    await _add_team_leader_roles(members, team_leaders)
    team_role = await guild.create_role(name=team_name, reason="Code Jam team creation")
    for entry in members:
        await entry["member"].add_roles(team_role)
    return team_role


async def create_team_channel(
        guild: discord.Guild,
        team_name: str,
        team_role: discord.Role

) -> int:
    """Create the team's text channel."""
    # Get permission overwrites and category
    team_channel_overwrites = _get_overwrites(guild, team_role)
    code_jam_category = await _get_category(guild)

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
            team_leaders: discord.PermissionOverwrite(read_messages=True),
            guild.get_role(Roles.code_jam_event_team): discord.PermissionOverwrite(read_messages=True)

        }
    )

    await _send_status_update(guild, f"Created {team_leaders_chat.mention} in the {category} category.")


async def _send_status_update(guild: discord.Guild, message: str) -> None:
    """Inform the events lead with a status update when the command is ran."""
    channel: discord.TextChannel = guild.get_channel(Channels.code_jam_planning)

    await channel.send(f"<@&{Roles.events_lead}>\n\n{message}")


async def _add_team_leader_roles(members: list[dict[str: discord.Member, str: bool]],
                                 team_leaders: discord.Role) -> None:
    """Assign the team leader role to the team leaders."""
    for entry in members:
        if entry["is_leader"]:
            await entry["member"].add_roles(team_leaders)


async def pin_message(message: discord.Message, ctx: commands.Context, unpin: bool) -> None:
    """Pin `message` if `pin` is True or unpin if it's False."""
    channel_str = f"#{message.channel} ({message.channel.id})"
    func = message.unpin if unpin else message.pin

    try:
        await func()
    except discord.HTTPException as e:
        if e.code == 10008:
            log.debug(f"Message {message.id} in {channel_str} doesn't exist; can't {func.__name__}.")
        else:
            log.exception(
                f"Error {func.__name__}ning message {message.id} in {channel_str}: "
                f"{e.status} ({e.code})"
            )
            await ctx.reply(f":x: Something went wrong with {func.__name__}ing your message!")
    else:
        log.trace(f"{func.__name__.capitalize()}ned message {message.id} in {channel_str}.")
        await ctx.reply(f":white_check_mark: Message has been {func.__name__}ed.")
