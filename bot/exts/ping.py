from disnake import Embed
from disnake.ext import commands

from bot.bot import SirRobin
from bot.log import log


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


def setup(bot: SirRobin) -> None:
    """Load the Ping cog."""
    bot.add_cog(Ping(bot))
