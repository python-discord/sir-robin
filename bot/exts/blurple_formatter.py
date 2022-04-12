import asyncio
import traceback

import discord
from botcore.utils.regex import FORMATTED_CODE_REGEX
from discord.ext import commands

from bot.bot import SirRobin
from bot.utils import blurple_formatter


class BlurpleFormatter(commands.Cog):
    """Format code in accordance with PEP 9001."""

    def __init__(self, bot: SirRobin):
        self.bot = bot
        self.lock = asyncio.Lock()

    @staticmethod
    def _format_code(code: str) -> str:
        blurpified = blurple_formatter.blurplify(code)
        blurpified = blurpified.replace("`", "`\u200d")
        return blurpified

    @commands.command(aliases=["blurp", "blurpify", "format"])
    async def blurplify(self, ctx: commands.Context, *, code: str) -> None:
        """Format code in accordance with PEP 9001."""
        if match := FORMATTED_CODE_REGEX.match(code):
            code = match.group("code")
        try:
            async with self.lock:
                blurpified = await asyncio.to_thread(self._format_code, code)
        except SyntaxError as e:
            err_info = "".join(traceback.format_exception_only(type(e), e)).replace("`", "`\u200d")
            embed = discord.Embed(
                title="Invalid Syntax!",
                description=f"```\n{err_info}\n```",
                color=0xCD6D6D,
            )
            await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            return

        await ctx.send(f"```py\n{blurpified}\n```", allowed_mentions=discord.AllowedMentions.none())


async def setup(bot: SirRobin) -> None:
    """Load the BlurpleFormatter cog."""
    await bot.add_cog(BlurpleFormatter(bot))
