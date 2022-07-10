from typing import TYPE_CHECKING, Callable

import discord
from botcore.site_api import ResponseCodeError
from botcore.utils.logging import get_logger

if TYPE_CHECKING:
    from bot.bot import SirRobin

from bot.constants import Channels, Roles

log = get_logger(__name__)


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
            team = await self.bot.code_jam_mgmt_api.get(f"users/{interaction.user.id}/current_team",
                                                        raise_for_status=True)
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
        await interaction.response.edit_message(view=self)
        self.stop()
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
