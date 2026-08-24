import asyncio
import json
import re
import textwrap
from os import environ
from pathlib import Path

import discord
from discord import Message, ui
from discord.ext import commands
from pydis_core.utils import scheduling
from pydis_core.utils.logging import get_logger

from bot import constants
from bot.bot import SirRobin

log = get_logger(__name__)

PIXELS_API_KEY_REGEX = re.compile(r"owl-[A-Za-z0-9\-\_]{86}")
PIXELS_JWT_REGEX = re.compile(r"e[yw][A-Za-z0-9-_]+\.(?:e[yw][A-Za-z0-9-_]+)?\.[A-Za-z0-9-_]{2,}")

REVOKED_MESSAGE = textwrap.dedent("""
:warning: Your message contained a valid Pixels API key or access token, which has been revoked.

Head to the [Pixels authorize page](<https://pixels.pythondiscord.com/auth/authorize>) to get a new API key.
""")

PIXELS_API_TOKEN_PATH = Path("/var/run/secrets/pixels-api/token")
PIXELS_URL = environ.get("PIXELS_URL", "https://pixels.pythondiscord.com")

class PixelsStreamView(ui.LayoutView):
    """LayoutView containing placement containers."""

    def __init__(self, containers: list[ui.Container]) -> None:
        super().__init__()
        for container in containers:
            self.add_item(container)


class Pixels(commands.Cog):
    """Utilities for working with Pixels API."""

    def __init__(self, bot: SirRobin):
        self.bot = bot
        self.stream_task: asyncio.Task | None = None
        self.flush_task: asyncio.Task | None = None
        self.bucket: list[ui.Container] = []
        self.bucket_lock = asyncio.Lock()

    async def cog_load(self) -> None:
        """Start background tasks for streaming and flushing placement buckets."""
        self.stream_task = scheduling.create_task(self.consume_stream())
        self.flush_task = scheduling.create_task(self.flush_bucket_loop())

    async def cog_unload(self) -> None:
        """Cancel background tasks on cog unload."""
        if self.stream_task:
            self.stream_task.cancel()
        if self.flush_task:
            self.flush_task.cancel()

    def get_request_headers(self) -> dict[str, str]:
        """Get the Pixels API request headers from the projected service account file."""
        with open(PIXELS_API_TOKEN_PATH) as f:
            token = f.read().strip()

        return {"Authorization": f"Token {token}"}

    async def consume_stream(self) -> None:
        """Consume the Pixels API event stream."""
        await self.bot.wait_until_ready()
        stream_url = f"{PIXELS_URL.rstrip('/')}/api/stream?no_current_state=true"

        while True:
            try:
                headers = self.get_request_headers()
                async with self.bot.http_session.get(stream_url, headers=headers) as resp:
                    if resp.status != 200:
                        log.error(f"Failed to connect to Pixels stream. Status code: {resp.status}")
                        await asyncio.sleep(5)
                        continue

                    log.info("Connected to Pixels API stream.")
                    current_event: str | None = None
                    current_data: list[str] = []

                    async for line_bytes in resp.content:
                        line = line_bytes.decode("utf-8").rstrip("\r\n")
                        if not line:
                            if current_event and current_data:
                                data_str = "\n".join(current_data)
                                await self.handle_stream_event(current_event, data_str)
                            current_event = None
                            current_data = []
                        elif line.startswith("event:"):
                            current_event = line[6:].strip()
                        elif line.startswith("data:"):
                            current_data.append(line[5:].strip())
            except asyncio.CancelledError:
                log.info("Pixels stream consumer task cancelled.")
                break
            except Exception:
                log.exception("Error consuming Pixels API stream.")
                await asyncio.sleep(5)

    async def handle_stream_event(self, event_type: str, data_str: str) -> None:
        """Handle an incoming event from the Pixels API stream."""
        try:
            payload = json.loads(data_str)
        except json.JSONDecodeError:
            log.warning(f"Failed to decode stream event data for event {event_type}: {data_str}")
            return

        user_id = payload.get("user_id")
        rgb = payload.get("rgb")
        x = payload.get("x")
        y = payload.get("y")
        if user_id is None or not rgb or x is None or y is None:
            log.warning(f"Event payload missing required fields: {payload}")
            return

        user_id_int = int(user_id)
        user = self.bot.get_user(user_id_int)
        if user is None:
            try:
                user = await self.bot.fetch_user(user_id_int)
            except discord.HTTPException:
                user = None

        if user:
            user_name = user.name
            avatar_url = user.display_avatar.url
        else:
            user_name = "Unknown User"
            avatar_url = self.bot.user.display_avatar.url

        rgb_hex = str(rgb).lstrip("#")
        try:
            colour = discord.Colour(int(rgb_hex, 16))
        except ValueError:
            colour = discord.Colour.default()

        container = ui.Container(accent_colour=colour)
        section = ui.Section(
            f"{user_name} (`{user_id_int}`) at ({x}, {y})",
            accessory=ui.Thumbnail(avatar_url),
        )
        container.add_item(section)

        await self.add_container_to_bucket(container)

    async def add_container_to_bucket(self, container: ui.Container) -> None:
        """Add a container to the batch bucket. If 10 containers are reached, send the bucket immediately."""
        async with self.bucket_lock:
            self.bucket.append(container)
            if len(self.bucket) >= 10:
                await self._send_bucket_locked()

    async def flush_bucket_loop(self) -> None:
        """Flush the bucket every 10 seconds if it contains any containers."""
        await self.bot.wait_until_ready()
        while True:
            try:
                await asyncio.sleep(10)
                async with self.bucket_lock:
                    if self.bucket:
                        await self._send_bucket_locked()
            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("Error in Pixels flush bucket loop.")

    async def _send_bucket_locked(self) -> None:
        """Send containers in the bucket as components v2 LayoutViews in batches of up to 10."""
        while self.bucket:
            containers_to_send = self.bucket[:10]
            self.bucket = self.bucket[10:]

            channel = self.bot.get_channel(constants.Channels.pixels_stream)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(constants.Channels.pixels_stream)
                except discord.HTTPException:
                    log.error(f"Could not fetch pixels stream channel (ID: {constants.Channels.pixels_stream}).")
                    return

            view = PixelsStreamView(containers_to_send)
            try:
                await channel.send(view=view)
            except discord.HTTPException:
                log.exception(f"Failed to post Pixels placement bucket to channel {channel.id}.")

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Check for exposed Pixels API keys and JWTs in messages."""
        if message.author.bot:
            return

        found_jwts = PIXELS_JWT_REGEX.findall(message.content)
        found_api_keys = PIXELS_API_KEY_REGEX.findall(message.content)
        any_invalidated = False

        if found_jwts or found_api_keys:
            headers = self.get_request_headers()
            log.info(f"Potential Pixels credentials in message {message.channel}/{message.id} by {message.author}.")
            # Call https://pixels.pythondiscord.com/api/invalidate_credential for each credential found

            for jwt in found_jwts:
                async with self.bot.http_session.post(
                    f"{PIXELS_URL.rstrip('/')}/api/invalidate_credential",
                    headers=headers,
                    json={"jwt": jwt},
                ) as resp:
                    if resp.status == 200:
                        log.info(f"Successfully invalidated Pixels JWT from {message.channel}/{message.id}")
                        any_invalidated = True
                    else:
                        if resp.status in (404, 400):
                            # False positive, the JWT is already invalid or didn't exist
                            continue

                        log.error(f"Failed to invalidate Pixels JWT: {jwt}. Status code: {resp.status}")

            for api_key in found_api_keys:
                async with self.bot.http_session.post(
                    f"{PIXELS_URL.rstrip('/')}/api/invalidate_credential",
                    headers=headers,
                    json={"api_key": api_key},
                ) as resp:
                    if resp.status == 200:
                        log.info(f"Successfully invalidated Pixels key from {message.channel}/{message.id}")
                        any_invalidated = True
                    else:
                        if resp.status in (404, 400):
                            # False positive, the API key is already invalid or didn't exist
                            continue

                        log.error(f"Failed to invalidate Pixels API key: {api_key}. Status code: {resp.status}")

            if any_invalidated:
                await message.channel.send(f"{message.author.mention} {REVOKED_MESSAGE}")
                await message.delete()
                log.info(f"Deleted message {message.channel}/{message.id} containing exposed Pixels credentials.")


async def setup(bot: SirRobin) -> None:
    """Load the Pixels cog."""
    if not PIXELS_API_TOKEN_PATH.exists():
        log.warning(f"Pixels API token file {PIXELS_API_TOKEN_PATH} does not exist. Skipping Pixels cog setup.")
        return

    await bot.add_cog(Pixels(bot))
