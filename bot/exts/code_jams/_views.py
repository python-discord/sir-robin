from typing import TYPE_CHECKING, Any, Callable, Optional

import discord
from botcore.site_api import APIClient, ResponseCodeError
from botcore.utils.logging import get_logger

if TYPE_CHECKING:
    from bot.bot import SirRobin

from bot.constants import Channels, Roles
from bot.utils.exceptions import JamCategoryNameConflictError

log = get_logger(__name__)


async def interaction_fetch_user_data(
        endpoint: str,
        mgmt_client: APIClient,
        interaction: discord.Interaction
) -> Optional[dict[str, Any]]:
    """A helper function for fetching and handling user related data in an interaction."""
    try:
        user = await mgmt_client.get(endpoint, raise_for_status=True)
    except ResponseCodeError as err:
        if err.response.status == 404:
            await interaction.response.send_message(":x: The user could not be found.", ephemeral=True)
        else:
            await interaction.response.send_message(
                ":x: Something went wrong! Full details have been logged.",
                ephemeral=True
            )
            log.error(f"Something went wrong: {err}")
        return
    else:
        return user


class JamTeamInfoConfirmation(discord.ui.View):
    """A basic view to confirm Team announcement."""

    def __init__(self, bot: 'SirRobin', guild: discord.Guild, original_author: discord.Member):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.original_author = original_author

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """A button to cancel the announcement."""
        button.label = "Cancelled"
        button.disabled = True
        self.announce.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label='Announce teams', style=discord.ButtonStyle.green)
    async def announce(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """A button to send the announcement."""
        button.label = "Teams have been announced!"
        button.disabled = True
        self.cancel.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)
        announcements = self.guild.get_channel(Channels.summer_code_jam_announcements)
        await announcements.send(
            f"<@&{Roles.code_jam_participants}> ! You have been sorted into a team!"
            " Click the button below to get a detailed description!",
            view=JamTeamInfoView(self.bot)
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Global check to ensure that the interacting user is the user who invoked the command originally."""
        if interaction.user != self.original_author:
            await interaction.response.send_message(
                ":x: You can't interact with someone else's response. Please run the command yourself!",
                ephemeral=True
            )
            return False
        return True


class JamTeamInfoView(discord.ui.View):
    """A persistent view to show Team related data to users."""

    def __init__(self, bot: 'SirRobin'):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Show me my team!", style=discord.ButtonStyle.blurple, custom_id="CJ:PERS:SHOW_TEAM")
    async def show_team(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """A button that sends an ephemeral embed with the team's description."""
        try:
            team = await self.bot.code_jam_mgmt_api.get(
                f"users/{interaction.user.id}/current_team",
                raise_for_status=True
            )
        except ResponseCodeError as err:
            if err.response.status == 404:
                await interaction.response.send_message("It seems like you're not a participant!", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "Something went wrong while processing the request! We have notified the team!",
                    ephemeral=True
                )
                log.error(err.response)
        else:
            response_embed = discord.Embed(
                title=f"You have been sorted into {team['team']['name']}",
                colour=discord.Colour.og_blurple()
            )
            team_channel = f"<#{team['team']['discord_channel_id']}>"
            team_members = [f"<@{member['user_id']}>" for member in team["team"]["users"]]
            response_embed.add_field(name="Your team's channel:", value=team_channel)
            response_embed.add_field(name="You teammates:", value="\n".join(team_members))
            response_embed.set_footer(text="Good luck!")
            await interaction.response.send_message(
                embed=response_embed,
                ephemeral=True
            )


class JamConfirmation(discord.ui.View):
    """A basic view to confirm the ending of a CJ."""

    def __init__(
            self,
            callback: Callable,
            author: discord.Member
    ):
        super().__init__()
        self.original_author = author
        self.callback = callback

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """A button to cancel an action."""
        button.label = "Cancelled"
        button.disabled = True
        self.confirm.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """A button to confirm an action."""
        button.label = "Confirmed"
        button.disabled = True
        self.cancel.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)
        await self.callback()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Global check to ensure that the interacting user is the user who invoked the command originally."""
        if interaction.user != self.original_author:
            await interaction.response.send_message(
                ":x: You can't interact with someone else's response. Please run the command yourself!",
                ephemeral=True
            )
            return False
        return True

    async def on_error(self, error: Exception, item: discord.ui.Item[Any], interaction: discord.Interaction) -> None:
        """Discord.py default to handle a view error."""
        if isinstance(error, JamCategoryNameConflictError):
            await interaction.channel.send(
                ":x: Due to a conflict regarding the names of the main Code Jam Category and the Code Jam Team category"
                " the Code Jam creation was aborted."
            )
        else:
            await interaction.channel.send(
                ":x: Something went wrong when confirming the view. Full details have been logged."
            )
            log.error(f"Something went wrong: {error}")


class AddNoteModal(discord.ui.Modal, title="Add a Note for a Code Jam Participant"):
    """A simple modal to add a note to a Jam participant."""

    def __init__(self, member: discord.Member, mgmt_client: APIClient):
        super().__init__()
        self.member = member
        self.mgmt_client = mgmt_client

    note = discord.ui.TextInput(
        label="Note",
        placeholder="Your note..."
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Discord.py default to handle modal submission."""
        if not (
                user := await interaction_fetch_user_data(
                    f"users/{self.member.id}/current_team",
                    self.mgmt_client,
                    interaction
                )
        ):
            return
        else:
            jam_id = user["team"]["jam_id"]
            try:
                await self.mgmt_client.post(
                    "infractions",
                    json={
                        "user_id": self.member.id,
                        "jam_id": jam_id, "reason": self.note.value,
                        "infraction_type": "note"
                    },
                    raise_for_status=True
                )
            except ResponseCodeError as err:
                if err.response.status == 404:
                    await interaction.response.send_message(
                        ":x: The user could not be found!",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        ":x: Something went wrong! Full details have been logged.",
                        ephemeral=True
                    )
                    log.error(f"Something went wrong: {err}")
                return
            else:
                await interaction.response.send_message('Your note has been saved!', ephemeral=True)

    async def on_error(self, error: Exception, interaction: discord.Interaction) -> None:
        """Discord.py default to handle modal error."""
        await interaction.response.send_message(":x: Something went wrong while processing your form.", ephemeral=True)


class JamInfoView(discord.ui.View):
    """
    A basic view that displays basic information about a CJ participant.

    Additionally, notes for a participant can be added and viewed.
    """

    def __init__(self, member: discord.Member, mgmt_client: APIClient, author: discord.Member):
        super().__init__(timeout=900)
        self.mgmt_client = mgmt_client
        self.member = member
        self.author = author

    @discord.ui.button(label='Add Note', style=discord.ButtonStyle.green)
    async def add_note(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """A button to add a note."""
        await interaction.response.send_modal(AddNoteModal(self.member, self.mgmt_client))

    @discord.ui.button(label='View notes', style=discord.ButtonStyle.green)
    async def view_notes(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """A button to view the notes of a participant."""
        if not (user := await interaction_fetch_user_data(f"users/{self.member.id}", self.mgmt_client, interaction)):
            return
        else:
            part_history = user["participation_history"]
            notes = []
            for entry in part_history:
                for infraction in entry["infractions"]:
                    notes.append(infraction)
            if not notes:
                await interaction.response.send_message(
                    f":x: {self.member.mention} doesn't have any notes yet.",
                    ephemeral=True
                )
            else:
                if len(notes) > 25:
                    notes = notes[:25]
                notes_embed = discord.Embed(title=f"Notes on {self.member.name}", colour=discord.Colour.orange())
                for note in notes:
                    notes_embed.add_field(name=f"Jam - (ID: {note['jam_id']})", value=note["reason"])
                await interaction.response.send_message(embed=notes_embed, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Global check to ensure the interacting user is an admin."""
        if interaction.guild.get_role(Roles.admins) in interaction.user.roles or interaction.user == self.author:
            return True
        await interaction.response.send_message(
            ":x: You don't have permission to interact with this view!",
            ephemeral=True
        )
        return False
