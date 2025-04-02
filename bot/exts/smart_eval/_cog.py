import asyncio
import random
import re

from async_rediscache import RedisCache
from discord.ext import commands
from pydis_core.utils.regex import FORMATTED_CODE_REGEX

from bot.bot import SirRobin
from bot.exts.smart_eval._smart_eval_rules import DEFAULT_RESPONSES, RULES
from bot.utils.uwu import uwuify

DONATION_LEVELS = {
    # Number of donations: (response time, intelligence level)
    0: (15, 0),
    10: (10, 1),
    20: (8, 2),
    30: (6, 3),
    40: (5, 4),
    50: (4, 5),
}

class SmartEval(commands.Cog):
    """Cog that handles all Smart Eval functionality."""

    #RedisCache[user_id: int, hardware: str]
    smarte_donation_cache = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot

    async def cog_load(self) -> None:
        """Run startup tasks needed when cog is first loaded."""

    async def get_gpu_capabilities(self) -> tuple[int, int]:
        """Get the GPU capabilites based on the number of donated GPUs."""
        total_donations = await self.total_donations()
        response_time, intelligence_level = DONATION_LEVELS[0]
        for donation_level, (time, max_response) in DONATION_LEVELS.items():
            if total_donations >= donation_level:
                response_time = time
                intelligence_level = max_response
            else:
                break

        return response_time, intelligence_level

    async def improve_gpu_name(self, hardware_name: str) -> str:
        """Quackify and pythonify the given GPU name."""
        hardware_name = hardware_name.replace("NVIDIA", "NQUACKIA")
        hardware_name = hardware_name.replace("Radeon", "Quackeon")
        hardware_name = hardware_name.replace("GeForce", "PyForce")
        hardware_name = hardware_name.replace("RTX", "PyTX")
        hardware_name = hardware_name.replace("RX", "PyX")
        hardware_name = hardware_name.replace("Iris", "Pyris")

        # Some adjustments to prevent low hanging markdown escape
        hardware_name = hardware_name.replace("*", "")
        hardware_name = hardware_name.replace("_", " ")

        return hardware_name

    @commands.command()
    async def donations(self, ctx: commands.Context) -> None:
        """Display the number of donations recieved so far."""
        total_donations = await self.total_donations()
        response_time, intelligence_level = await self.get_gpu_capabilities()
        msg = (
            f"Currently, I have received {total_donations} GPU donations, "
            f"and am at intelligence level {intelligence_level}! "
        )

        # Calculate donations needed to reach next intelligence level
        donations_needed = 0
        for donation_level in DONATION_LEVELS:
            if donation_level > total_donations:
                donations_needed = donation_level - total_donations
                break

        if donations_needed:
            msg += (
                f"\n\nTo reach the next intelligence level, I need {donations_needed} more donations! "
                f"Please consider donating your GPU to help me out. "
            )

        await ctx.reply(msg)

    async def total_donations(self) -> int:
        """Get the total number of donations."""
        return await self.smarte_donation_cache.length()

    @commands.command(aliases=[])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def donate(self, ctx: commands.Context, *, hardware: str | None = None) -> None:
        """
        Donate your GPU to help power our Smart Eval command.

        Provide the name of your GPU when running the command.
        """
        if await self.smarte_donation_cache.contains(ctx.author.id):
            stored_hardware = await self.smarte_donation_cache.get(ctx.author.id)
            await ctx.reply(
                "I can only take one donation per person. "
                f"Thank you for donating your *{stored_hardware}* to our Smart Eval command."
            )
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

        if len(hardware) > 255:
            await ctx.reply(
                "This hardware name is too complicated, I don't have the context window "
                "to remember that"
            )
            return

        msg = "Thank you for donating your GPU to our Smart Eval command."
        fake_hardware = await self.improve_gpu_name(hardware)
        await self.smarte_donation_cache.set(ctx.author.id, fake_hardware)

        if fake_hardware != hardware:
            msg += (
                f" I did decide that instead of *{hardware}*, it would be better if you donated *{fake_hardware}*."
                " So I've recorded that GPU donation instead."
            )
        msg += "\n\nIt will be used wisely and definitely not for shenanigans!"
        await ctx.reply(msg)

    @commands.command(aliases=["smarte"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def smart_eval(self, ctx: commands.Context, *, code: str) -> None:
        """Evaluate your Python code with PyDis's newest chatbot."""
        response_time, intelligence_level = await self.get_gpu_capabilities()

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
                    matches = match.groups()
                    if len(matches) > 0:
                        matching_responses.append(response.format(*matches))
                    else:
                        matching_responses.append(response)
        if not matching_responses:
            matching_responses = DEFAULT_RESPONSES

        selected_response = random.choice(matching_responses)
        if random.randint(1,5) == 5:
            selected_response = uwuify(selected_response)

        async with ctx.typing():
            await asyncio.sleep(response_time)

            if len(selected_response) <= 1000:
                await ctx.reply(selected_response)
            else:
                await ctx.reply(
                    "There's definitely something wrong but I'm just not sure how to put it concisely into words."
                )
