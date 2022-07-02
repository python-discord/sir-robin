import unittest
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch, call

from discord import CategoryChannel
from discord.ext.commands import BadArgument

from bot.constants import Roles
from bot.exts import code_jams
from bot.exts.code_jams import _cog, _creation_utils
from tests.helpers import (
    MockAttachment, MockBot, MockCategoryChannel, MockContext, MockGuild, MockMember, MockRole, MockTextChannel,
    autospec
)

TEST_CSV = b"""\
Team Name,Team Member Discord ID,Team Leader
Annoyed Alligators,12345,Y
Annoyed Alligators,54321,N
Oscillating Otters,12358,Y
Oscillating Otters,74832,N
Oscillating Otters,19903,N
Annoyed Alligators,11111,N
"""


def get_mock_category(channel_count: int, name: str) -> CategoryChannel:
    """Return a mocked code jam category."""
    category = create_autospec(CategoryChannel, spec_set=True, instance=True)
    category.name = name
    category.channels = [MockTextChannel() for _ in range(channel_count)]

    return category


class JamCodejamCreateTests(unittest.IsolatedAsyncioTestCase):
    """Tests for `codejam create` command."""

    def setUp(self):
        self.bot = MockBot()
        self.admin_role = MockRole(name="Admins", id=Roles.admins)
        self.command_user = MockMember([self.admin_role])
        self.guild = MockGuild([self.admin_role])
        self.ctx = MockContext(bot=self.bot, author=self.command_user, guild=self.guild)
        self.cog = _cog.CodeJams(self.bot)

    async def test_message_without_attachments(self):
        """If no link or attachments are provided, commands.BadArgument should be raised."""
        self.ctx.message.attachments = []

        with self.assertRaises(BadArgument):
            await self.cog.create(self.cog, self.ctx, None)

    @patch.object(_creation_utils, "create_team_channel")
    @patch.object(_creation_utils, "create_team_leader_channel")
    @patch.object(_creation_utils, "create_team_role")
    async def test_result_sending(self, create_team_role, create_team_leader_channel, create_team_channel):
        """Should call `ctx.send` when everything goes right."""
        self.ctx.message.attachments = [MockAttachment()]
        self.ctx.message.attachments[0].read = AsyncMock()
        self.ctx.message.attachments[0].read.return_value = TEST_CSV

        team_leaders = MockRole()

        self.guild.get_member.return_value = MockMember()

        self.ctx.guild.create_role = AsyncMock()
        self.ctx.guild.create_role.return_value = team_leaders
        self.cog.add_roles = AsyncMock()
        teams = {"Team": [{"member": MockMember(), "is_leader": True}]}

        await _cog.creation_flow(self.ctx, teams, AsyncMock())
        create_team_channel.assert_awaited_once()
        create_team_role.assert_awaited_once()
        create_team_leader_channel.assert_awaited_once_with(
            self.ctx.guild, team_leaders
        )
        self.ctx.send.assert_awaited_once()

    async def test_link_returning_non_200_status(self):
        """When the URL passed returns a non 200 status, it should send a message informing them."""
        self.bot.http_session.get.return_value = mock = MagicMock()
        mock.status = 404
        await self.cog.create(self.cog, self.ctx, "https://not-a-real-link.com")

        self.ctx.send.assert_awaited_once()

    @patch.object(_creation_utils, "_send_status_update")
    async def test_category_doesnt_exist(self, update):
        """Should create a new code jam category."""
        subtests = (
            [],
            [get_mock_category(_creation_utils.MAX_CHANNELS, _creation_utils.CATEGORY_NAME)],
            [get_mock_category(_creation_utils.MAX_CHANNELS - 2, "other")],
        )

        for categories in subtests:
            update.reset_mock()
            self.guild.reset_mock()
            self.guild.categories = categories

            with self.subTest(categories=categories):
                actual_category = await _creation_utils._get_category(self.guild)

                update.assert_called_once()
                self.guild.create_category_channel.assert_awaited_once()
                category_overwrites = self.guild.create_category_channel.call_args[1]["overwrites"]

                self.assertFalse(category_overwrites[self.guild.default_role].read_messages)
                self.assertTrue(category_overwrites[self.guild.me].read_messages)
                self.assertEqual(self.guild.create_category_channel.return_value, actual_category)

    async def test_category_channel_exist(self):
        """Should not try to create category channel."""
        expected_category = get_mock_category(_creation_utils.MAX_CHANNELS - 2, _creation_utils.CATEGORY_NAME)
        self.guild.categories = [
            get_mock_category(_creation_utils.MAX_CHANNELS - 2, "other"),
            expected_category,
            get_mock_category(0, _creation_utils.CATEGORY_NAME),
        ]

        actual_category = await _creation_utils._get_category(self.guild)
        self.assertEqual(expected_category, actual_category)

    async def test_channel_overwrites(self):
        """Should have correct permission overwrites for users and roles."""
        role = MockRole()
        overwrites = _creation_utils._get_overwrites(self.guild, role)
        self.assertTrue(overwrites[role].read_messages)

    @patch.object(_creation_utils, "_get_overwrites")
    @patch.object(_creation_utils, "_get_category")
    @autospec(_creation_utils, "_add_team_leader_roles", pass_mocks=False)
    async def test_team_channels_creation(self, get_category, get_overwrites):
        """Should create a text channel for a team."""
        team_leaders = MockRole()
        team_role = MockRole()
        category = MockCategoryChannel()
        category.create_text_channel = AsyncMock()

        get_category.return_value = category
        await _creation_utils.create_team_channel(self.guild, "my-team", team_role)

        category.create_text_channel.assert_awaited_once_with(
            "my-team",
            overwrites=get_overwrites.return_value
        )
    async def test_jam_normal_roles_adding(self):
        """Should add the Jam team role to every team member, and Team Lead Role to Team Leads."""
        leader = MockMember()
        leader_role = MockRole(name="Team Leader")
        members = [{"member": leader, "is_leader": True}] + [{"member": MockMember(), "is_leader": False} for _ in
                                                                   range(4)]
        team_role = await _creation_utils.create_team_role(MockGuild(), team_name="Team", members=members,
                                                           team_leaders=leader_role)
        for entry in members:
            if not entry["is_leader"]:
                entry["member"].add_roles.assert_awaited_once_with(team_role)
            else:
                entry["member"].add_roles.assert_has_calls([call(team_role), call(leader_role)], any_order=True)
                self.assertTrue(entry["member"].add_roles.call_count == 2)


class CodeJamSetup(unittest.IsolatedAsyncioTestCase):
    """Test for `setup` function of `CodeJam` cog."""

    async def test_setup(self):
        """Should call `bot.add_cog`."""
        bot = MockBot()
        await code_jams.setup(bot)
        bot.add_cog.assert_awaited_once()
