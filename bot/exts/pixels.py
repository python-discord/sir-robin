import re
import textwrap
from pathlib import Path

from discord import Message
from discord.ext import commands
from pydis_core.utils.logging import get_logger

from bot.bot import SirRobin

log = get_logger(__name__)

PIXELS_API_KEY_REGEX = re.compile(r"owl-[A-Za-z0-9\-\_]{86}")
PIXELS_JWT_REGEX = re.compile(r"e[yw][A-Za-z0-9-_]+\.(?:e[yw][A-Za-z0-9-_]+)?\.[A-Za-z0-9-_]{2,}")

REVOKED_MESSAGE = textwrap.dedent("""
:warning: Your message contained a valid Pixels API key or access token, which has been revoked.

Visit [`/auth/authorize`](https://pixels.pythondiscord.com/auth/authorize) to generate a new API key.
""")

PIXELS_API_TOKEN_PATH = Path("/var/run/secrets/pixels-api/token")

class Pixels(commands.Cog):
    """Utilities for working with Pixels API."""

    def __init__(self, bot: SirRobin):
        self.bot = bot

    def get_request_headers(self) -> dict[str, str]:
        """Get the Pixels API request headers from the projected service account file."""
        with open(PIXELS_API_TOKEN_PATH) as f:
            token = f.read().strip()

        return {"Authorization": f"Token {token}"}

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
                    "https://pixels.pythondiscord.com/api/invalidate_credential",
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
                    "https://pixels.pythondiscord.com/api/invalidate_credential",
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
                await message.channel.send(REVOKED_MESSAGE)
                await message.delete()
                log.info(f"Deleted message {message.channel}/{message.id} containing exposed Pixels credentials.")


async def setup(bot: SirRobin) -> None:
    """Load the Pixels cog."""
    if not PIXELS_API_TOKEN_PATH.exists():
        log.warning(f"Pixels API token file {PIXELS_API_TOKEN_PATH} does not exist. Skipping Pixels cog setup.")
        return

    await bot.add_cog(Pixels(bot))
