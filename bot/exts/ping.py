from botcore.utils.logging import get_logger
from discord import Embed
from discord.ext import commands

from bot.bot import SirRobin

log = get_logger(__name__)


class Ping(commands.Cog):
    """Send an embed about the bot's ping."""

    def __init__(self, bot: SirRobin):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        """Ping the bot to see its latency and state."""
        log.debug(f"Command `{ctx.invoked_with}` used by {ctx.author}.")
        embed = Embed(
            title=":ping_pong: Pong!",
            description=f"Gateway Latency: {round(self.bot.latency * 1000)}ms",
        )

        await ctx.send(embed=embed)


async def setup(bot: SirRobin) -> None:
    """Load the Ping cog."""
    await bot.add_cog(Ping(bot))
