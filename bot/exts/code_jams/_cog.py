import csv
from collections import defaultdict
from functools import partial

import discord
from discord import Colour, Embed, Guild, Member
from discord.ext import commands
from pydis_core.site_api import APIClient, ResponseCodeError
from pydis_core.utils.logging import get_logger
from pydis_core.utils.members import get_or_fetch_member
from pydis_core.utils.paste_service import PasteFile, PasteTooLongError, PasteUploadError, send_to_paste_service

from bot.bot import SirRobin
from bot.constants import Emojis, Roles
from bot.exts.code_jams import _creation_utils
from bot.exts.code_jams._flows import add_flow, creation_flow, deletion_flow, move_flow, pin_flow, remove_flow
from bot.exts.code_jams._views import JamConfirmation, JamInfoView, JamTeamInfoConfirmation
from bot.utils.checks import in_code_jam_category
from bot.utils.decorators import with_role

log = get_logger(__name__)
PIN_ALLOWED_ROLES: tuple[int, ...] = (Roles.admins, Roles.code_jam_event_team)


class CodeJams(commands.Cog):
    """Manages the code-jam related parts of our server."""

    def __init__(self, bot: SirRobin):
        self.bot = bot

    @commands.group(aliases=("cj", "jam"))
    async def codejam(self, ctx: commands.Context) -> None:
        """A Group of commands for managing Code Jams."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.events_lead)
    async def create(self, ctx: commands.Context, csv_file: str | None = None) -> None:
        """
        Create code-jam teams from a CSV file or a link to one, specifying the team names, leaders and members.

        The CSV file must have 3 columns: 'Team Name', 'Team Member Discord ID', and 'Team Leader'.

        This will create the text channels for the teams, and give the team leaders their roles.
        """
        async with ctx.typing():
            if csv_file:
                async with self.bot.http_session.get(csv_file) as response:
                    if response.status != 200:
                        await ctx.send(f"Got a bad response from the URL: {response.status}")
                        return

                    csv_file = await response.text()

            elif ctx.message.attachments:
                csv_file = (await ctx.message.attachments[0].read()).decode("utf8")
            else:
                raise commands.BadArgument("You must include either a CSV file or a link to one.")

            teams = defaultdict(list)
            reader = csv.DictReader(csv_file.splitlines())

            for row in reader:
                member = await get_or_fetch_member(ctx.guild, int(row["Team Member Discord ID"]))

                if member is None:
                    log.trace(f"Got an invalid member ID: {row['Team Member Discord ID']}")
                    continue

                teams[row["Team Name"]].append({"member": member, "is_leader": row["Team Leader"].upper() == "Y"})
            warning_embed = Embed(
                colour=discord.Colour.orange(),
                title="Warning!",
                description=f"{len(teams)} teams and roles will be created, are you sure?"
            )
            warning_embed.set_footer(text="Code Jam team generation")
            callback = partial(creation_flow, ctx, teams, self.bot)
            await ctx.send(
                embed=warning_embed,
                view=JamConfirmation(author=ctx.author, callback=callback)
            )

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.events_lead)
    async def announce(self, ctx: commands.Context) -> None:
        """A command to send an announcement embed to the CJ announcement channel."""
        team_info_view = JamTeamInfoConfirmation(self.bot, ctx.guild, ctx.author)
        embed_conf = Embed(title="Would you like to announce the teams?", colour=discord.Colour.og_blurple())
        await ctx.send(
            embed=embed_conf,
            view=team_info_view
        )

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.events_lead)
    async def end(self, ctx: commands.Context) -> None:
        """
        Delete all code jam channels.

        A confirmation message is displayed with the categories and channels
        that are going to be deleted, by pressing "Confirm" the deletion
        process will begin.
        """
        categories = self.jam_categories(ctx.guild)
        roles = await self.jam_roles(ctx.guild, self.bot.code_jam_mgmt_api)
        if not categories and not roles:
            await ctx.send(":x: The Code Jam channels and roles have already been deleted! ")
            return

        category_channels: dict[discord.CategoryChannel: list[discord.TextChannel]] = {
            category: category.channels.copy() for category in categories
        }

        details = "Categories and Channels: \n"
        for category, channels in category_channels.items():
            details += f"{category.name}[{category.id}]: {','.join([channel.name for channel in channels])}\n"
        details += "Roles:\n"
        for role in roles:
            details += f"{role.name}[{role.id}]\n"
        paste_file = PasteFile(content=details)
        try:
            paste_response = await send_to_paste_service(
                files=[paste_file],
                http_session=self.bot.http_session,
            )
            url = paste_response.link
        except PasteUploadError:
            log.exception("Generic upload error from paste service:")
            url = "**Unable to send deletion details to the pasting service.**"
        except PasteTooLongError:
            url = "**Unable to send deletion details to the pasting service, content too long**"
        warning_embed = Embed(title="Are you sure?", colour=discord.Colour.orange())
        warning_embed.add_field(
            name="For a detailed list of which roles, categories and channels will be deleted see:",
            value=url
        )
        callback = partial(deletion_flow, category_channels, roles)
        confirm_view = JamConfirmation(author=ctx.author, callback=callback)
        await ctx.send(
            embed=warning_embed,
            view=confirm_view
        )
        await confirm_view.wait()
        await ctx.send("Code Jam has officially ended! :sunrise:")

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.code_jam_event_team)
    async def info(self, ctx: commands.Context, member: Member) -> None:
        """
        Send an info embed about the member with the team they're in.

        The team is found by issuing a request to the CJ Management System
        """
        try:
            team = await self.bot.code_jam_mgmt_api.get(
                f"users/{member.id}/current_team",
                raise_for_status=True
            )
        except ResponseCodeError as err:
            if err.response.status == 404:
                await ctx.send(":x: It seems like the user is not a participant!")
            else:
                await ctx.send("Something went wrong while processing the request! We have notified the team!")
                log.error(f"Something went wrong with processing the request! {err}")
        else:
            embed = Embed(
                title=str(member),
                colour=Colour.og_blurple()
            )
            embed.add_field(name="Team", value=team["team"]["name"], inline=True)
            embed.add_field(name="Team leader", value="Yes" if team["is_leader"] else "No", inline=True)
            await ctx.send(embed=embed, view=JamInfoView(member, self.bot.code_jam_mgmt_api, ctx.author))

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.events_lead)
    async def move(self, ctx: commands.Context, member: Member, *, new_team_name: str) -> None:
        """Move participant from one team to another by issuing an HTTP request to the Code Jam Management system."""
        callback = partial(move_flow, self.bot, new_team_name, ctx, member)
        await ctx.send(
            f"Are you sure you want to move {member.mention} to {new_team_name}?",
            view=JamConfirmation(author=ctx.author, callback=callback)
        )

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.events_lead)
    async def add(
            self,
            ctx: commands.Context,
            member: Member,
            is_leader: bool = False,
            *,
            team_name: str
    ) -> None:
        """Add a member to the Code Jam by specifying the team's name, and whether they should be leaders."""
        callback = partial(add_flow, self.bot, team_name, ctx, member, is_leader)
        await ctx.send(
            f"Are you sure you want to add {member.mention} to {team_name}?",
            view=JamConfirmation(author=ctx.author, callback=callback)
        )

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.events_lead)
    async def remove(self, ctx: commands.Context, member: Member) -> None:
        """Remove the participant from their team. Does not remove the participants or leader roles."""
        callback = partial(remove_flow, self.bot, member, ctx)
        await ctx.send(
            f"Are you sure you want to remove {member.mention} from the Code Jam?",
            view=JamConfirmation(author=ctx.author, callback=callback)
        )

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.events_lead, Roles.code_jam_event_team, Roles.code_jam_participants)
    @in_code_jam_category(_creation_utils.CATEGORY_NAME)
    async def pin(self, ctx: commands.Context, message: discord.Message | None = None) -> None:
        """Lets Code Jam Participants to pin messages in their team channels."""
        await pin_flow(ctx, PIN_ALLOWED_ROLES, self.bot.code_jam_mgmt_api, message)

    @codejam.command()
    @commands.has_any_role(Roles.admins, Roles.events_lead, Roles.code_jam_event_team, Roles.code_jam_participants)
    @in_code_jam_category(_creation_utils.CATEGORY_NAME)
    async def unpin(self, ctx: commands.Context, message: discord.Message | None = None) -> None:
        """Lets Code Jam Participants to unpin messages in their team channels."""
        await pin_flow(ctx, PIN_ALLOWED_ROLES, self.bot.code_jam_mgmt_api, message, True)

    @codejam.group()
    @with_role(Roles.admins, Roles.code_jam_event_team, fail_silently=True)
    async def support(self, ctx: commands.Context) -> None:
        """Apply or remove the Code Jam Support role."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @support.command()
    @with_role(Roles.admins, Roles.code_jam_event_team, fail_silently=True)
    async def off(self, ctx: commands.Context) -> None:
        """Remove the Code Jam Support role."""
        user = ctx.author
        cj_support_role = ctx.guild.get_role(Roles.code_jam_support)

        if cj_support_role not in user.roles:
            await ctx.send(":question: You don't have the role.")
            return

        await user.remove_roles(cj_support_role)
        await ctx.send(f"{Emojis.check_mark} Code Jam Support role has been removed.")

    @support.command()
    @with_role(Roles.admins, Roles.code_jam_event_team, fail_silently=True)
    async def on(self, ctx: commands.Context) -> None:
        """Add the Code Jam Support role."""
        user = ctx.author
        cj_support_role = ctx.guild.get_role(Roles.code_jam_support)

        if cj_support_role in user.roles:
            await ctx.send(":question: You already have the role.")
            return

        await user.add_roles(cj_support_role)
        await ctx.send(f"{Emojis.check_mark} Code Jam Support role has been applied.")

    @codejam.command("ping")
    @commands.has_any_role(Roles.admins, Roles.events_lead, Roles.code_jam_event_team, Roles.code_jam_participants)
    @in_code_jam_category(_creation_utils.CATEGORY_NAME)
    async def ping_codejam_team(self, ctx: commands.Context) -> None:
        """Ping the team role for the channel this command is ran in."""
        team_resp = await self.bot.code_jam_mgmt_api.get(
            "teams/find",
            params={"name": ctx.channel.name.replace("-", " ")}  # Discord channels have hyphens, CJMS has spaces.
        )
        role_id = team_resp.get("discord_role_id")
        if not role_id:
            log.error("Failed to find '%s' in CJMS.", ctx.channel.name)
            await ctx.send("Failed to find team role id in database.")
            return
        await ctx.send(f"<@&{role_id}>")

    @staticmethod
    def jam_categories(guild: Guild) -> list[discord.CategoryChannel]:
        """Get all the code jam team categories."""
        return [category for category in guild.categories if category.name == _creation_utils.CATEGORY_NAME]

    @staticmethod
    async def jam_roles(guild: Guild, mgmt_client: APIClient) -> list[discord.Role] | None:
        """Get all the code jam team roles."""
        try:
            roles_raw = await mgmt_client.get("teams", raise_for_status=True, params={"current_jam": "true"})
        except ResponseCodeError:
            log.error("Could not fetch Roles from the Code Jam Management API")
            return None
        else:
            roles = []
            for role in roles_raw:
                if role := guild.get_role(role["discord_role_id"]):
                    roles.append(role)
            return roles

    @staticmethod
    def team_channel(guild: Guild, criterion: str | Member) -> discord.TextChannel | None:
        """Get a team channel through either a participant or the team name."""
        for category in CodeJams.jam_categories(guild):
            for channel in category.channels:
                if isinstance(channel, discord.TextChannel):
                    if (
                            # If it's a string.
                            criterion == channel.name or criterion == CodeJams.team_name(channel)
                            # If it's a member.
                            or criterion in channel.overwrites
                    ):
                        return channel
        return None

    @staticmethod
    def team_name(channel: discord.TextChannel) -> str:
        """Retrieves the team name from the given channel."""
        return channel.name.replace("-", " ").title()
