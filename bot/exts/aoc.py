from typing import Optional
import discord
from discord.ext import commands, tasks
from discord.utils import MISSING

from bot.bot import SirRobin
from bot import constants

aoc_URL = "https://adventofcode.com/{year}/day/{day}"

class OffSeasonAoC(commands.Cog):
    def __init__(self, bot: SirRobin) -> None:
        self.bot = bot
        self.loop: Optional[tasks.Loop] = None

        self.year: Optional[int] = None
        self.current_day: Optional[int] = None

    async def aoc_task(self) -> None:
        if self.current_day > 25:
            self.loop.cancel()
            return
        
        channel: discord.ForumChannel = self.bot.get_channel(constants.Channels.aoc_forum_channel)
        link = aoc_URL.format(year=self.year, day=self.current_day)
        await channel.create_thread(name=f"Off-season AoC #{self.current_day}", content=link)
        
        self.current_day += 1

    @commands.command()
    async def summer_aoc(self, ctx: commands.Context, year: int, days: int, start_day: int = 1) -> None:
        if not (year >= 2015 and year <= 2021):
            raise commands.BadArgument("Year must be between 2015 and 2021, inclusive")
        
        if not (start_day >= 1 and start_day <= 25):
            raise commands.BadArgument("Start day must be between 1 and 25, inclusive")

        self.year = year
        self.current_day = start_day

        if self.loop:
            await ctx.send("A loop is already running!")
        else:
            await ctx.send("Starting loop...")
            self.loop = tasks.Loop(
                self.aoc_task, 
                seconds=0, 
                minutes=0, 
                hours=(days * 24), 
                time=MISSING, 
                count=None, 
                reconnect=True
            )

            self.loop.start()

    @commands.command()
    async def stop_aoc(self, ctx: commands.Context) -> None:
        if self.loop:
            self.loop.cancel() # .cancel() doesn't allow the current iteration to finish
            await ctx.send("Stopped running AoC loop")
        else:
            await ctx.send("The AoC loop is currently not running.")
        
async def setup(bot: SirRobin):
    """Load the summer AoC cog"""
    await bot.add_cog(OffSeasonAoC(bot))