from botcore.utils.regex import FORMATTED_CODE_REGEX
from discord.ext import commands

from bot.bot import SirRobin
from bot.utils import blurple_formatter


class BlurpleFormatter(commands.Cog):
    """Format code in accordance with PEP 9001."""

    def __init__(self, bot: SirRobin):
        self.bot = bot

    @commands.command()
    async def blurplify(self, ctx: commands.Context, *, code: str) -> None:
        """Format code in accordance with PEP 9001."""
        if match := FORMATTED_CODE_REGEX.match(code):
            code = match.group("code")
        try:
            blurpified = blurple_formatter.blurplify(code)
        except SyntaxError:
            raise commands.BadArgument("Invalid Syntax!")
        blurpified = blurpified.replace("`", "`\u200d")
        await ctx.send(f"```py\n{blurpified}\n```")


async def setup(bot: SirRobin) -> None:
    """Load the BlurpleFormatter cog."""
    await bot.add_cog(BlurpleFormatter(bot))
