import logging

from disnake import Embed
from disnake.ext import commands


logger = logging.getLogger(__name__)


class Ping(commands.Cog):
    """Send an embed about the bot's ping."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        """Ping the bot to see its latency and state."""
        logger.debug(f"Command `{ctx.invoked_with}` used by {ctx.author}.")
        embed = Embed(
            title=":ping_pong: Pong!",
            description=f"Gateway Latency: {round(self.bot.latency * 1000)}ms",
        )

        await ctx.send(embed=embed)


def setup(bot: commands.Bot) -> None:
    """Load the Ping cog."""
    bot.add_cog(Ping(bot))
