import random
import re

from async_rediscache import RedisCache
from discord.ext import commands
from pydis_core.utils.regex import FORMATTED_CODE_REGEX

from bot.bot import SirRobin
from bot.exts.smart_eval._smart_eval_rules import DEFAULT_RESPONSES, RULES


class SmartEval(commands.Cog):
    """Cog that handles all Smart Eval functionality."""

    #RedisCache[user_id: int, hardware: str]
    smarte_donation_cache = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot

    async def cog_load(self) -> None:
        """Run startup tasks needed when cog is first loaded."""
        self.total_donations = await self.smarte_donation_cache.length()

    @commands.command(aliases=[])
    async def donate(self, ctx: commands.Context, *, hardware: str | None = None) -> None:
        """
        Donate your GPU to help power our Smart Eval command.

        Provide the name of your GPU when running the command.
        """
        if await self.smarte_donation_cache.contains(ctx.author.id):
            stored_hardware = await self.smarte_donation_cache.get(ctx.author.id)
            await ctx.reply(f"Thank you for donating your {stored_hardware} to our Smart Eval command.")
            return

        if hardware is None:
            await ctx.reply(
                "Thank you for your interest in donating your hardware to support my Smart Eval command."
                " If you provide the name of your GPU, through the magic of the internet, "
                "I will be able to use the GPU it to improve my Smart Eval outputs."
                " \n\nTo donate, re-run the donate command specifying your hardware: "
                "`&donate Your Hardware Name Goes Here`."
            )
            return

        fake_hardware = ... # Do some regex to pull out a semi-matching type of GPU and insert something else
        await self.smarte_donation_cache.set(ctx.author.id, hardware)

        self.total_donations = await self.smarte_donation_cache.length()
        await ctx.reply(
            "Thank you for donating your GPU to our Smart Eval command!"
            f" I did decide that instead of {hardware}, it would be better if you donated {fake_hardware}."
            " So I've recorded that GPU donaton instead."
            " It will be used wisely and definitely not for shenanigans."
        )

    @commands.command(aliases=["smarte"])
    async def smart_eval(self, ctx: commands.Context, *, code: str) -> None:
        """Evaluate your Python code with PyDis's newest chatbot."""
        if match := FORMATTED_CODE_REGEX.match(code):
            code = match.group("code")
        else:
            await ctx.reply(
                "Uh oh! You didn't post anything I can recognize as code. Please put it in a codeblock."
            )
            return

        matching_responses = []

        for pattern, responses in RULES.items():
            match = re.search(pattern, code)
            if match:
                for response in responses:
                    try:
                        matching_responses.append(response.format(match.group("content")))
                    except IndexError:
                        matching_responses.append(response)

        if not matching_responses:
            matching_responses = DEFAULT_RESPONSES
        final_response = random.choice(matching_responses)

        await ctx.reply(final_response)
