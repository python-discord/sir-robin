import json
import unittest
from unittest.mock import MagicMock

import discord

from bot.exts.pixels import Pixels, PixelsStreamView
from tests.helpers import MockBot, MockTextChannel


class PixelsCogTests(unittest.IsolatedAsyncioTestCase):
    """Tests for Pixels cog streaming and batching functionality."""

    def setUp(self) -> None:
        self.bot = MockBot()
        self.cog = Pixels(self.bot)

    async def test_handle_stream_event_creates_container(self) -> None:
        """Placement events should create a container and add it to bucket."""
        user = MagicMock(spec=discord.User)
        user.name = "TestUser"
        user.id = 123456789
        user.display_avatar.url = "http://avatar.url/1.png"
        self.bot.get_user.return_value = user

        event_data = json.dumps({"x": 10, "y": 20, "rgb": "FF0000", "user_id": 123456789})
        await self.cog.handle_stream_event("UPDATE", event_data)

        self.assertEqual(len(self.cog.bucket), 1)
        container = self.cog.bucket[0]
        self.assertIsInstance(container, discord.ui.Container)
        self.assertEqual(container.accent_colour.value, 0xFF0000)

    async def test_bucket_sends_when_10_containers_reached(self) -> None:
        """Bucket should flush automatically when 10 containers are reached."""
        channel = MockTextChannel()
        self.bot.get_channel.return_value = channel

        user = MagicMock(spec=discord.User)
        user.name = "TestUser"
        user.id = 123456789
        user.display_avatar.url = "http://avatar.url/1.png"
        self.bot.get_user.return_value = user

        event_data = json.dumps({"x": 10, "y": 20, "rgb": "00FF00", "user_id": 123456789})
        for _ in range(10):
            await self.cog.handle_stream_event("UPDATE", event_data)

        self.assertEqual(len(self.cog.bucket), 0)
        channel.send.assert_called_once()
        _, kwargs = channel.send.call_args
        self.assertIn("view", kwargs)
        self.assertIsInstance(kwargs["view"], PixelsStreamView)
        self.assertEqual(len(kwargs["view"].children), 10)
