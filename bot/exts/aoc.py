import logging
from typing import Optional

import arrow
import asyncio
import discord
from async_rediscache import RedisCache
from datetime import timedelta
from discord.ext import commands, tasks
from discord.utils import MISSING

from bot import constants
from bot.bot import SirRobin


log = logging.getLogger(__name__)

AOC_URL = "https://adventofcode.com/{year}/day/{day}"
LAST_DAY = 25
FIRST_YEAR = 2015
POST_TIME = 5  # UTC


INFO_TEMPLATE = """
is_running: {is_running}
\twait_task active: {wait_task_active}
\tloop_task active: {loop_task_active}

year: {year}
current_day: {current_day}
day_interval: {day_interval}

POST_TIME: {post_time}:00 UTC
FIRST_YEAR: {first_year}
LAST_DAY: {last_day}
"""

class OffSeasonAoC(commands.Cog):
    """Cog that handles all off season advent of code (AoC) functionality."""

    cache = RedisCache()

    def __init__(self, bot: SirRobin) -> None:
        self.bot = bot
        self.wait_task: Optional[asyncio.Task] = None
        self.loop_task: Optional[tasks.Loop] = None

        self.year: Optional[int] = None
        self.current_day: Optional[int] = None
        self.day_interval: Optional[int] = None
    
    @property
    def is_running(self) -> bool:
        waiting = (self.wait_task is not None) and not self.wait_task.done()
        looping = (self.loop_task is not None) and self.loop_task.is_running()
        return waiting or looping

    @commands.command()
    async def info(self, ctx: commands.Context) -> None:
        """Give info about the state of the event."""
        msg = INFO_TEMPLATE.format(
            is_running=self.is_running,
            wait_task_active=(self.wait_task is not None) and not self.wait_task.done(),
            loop_task_active=(self.loop_task is not None) and self.loop_task.is_running(),
            year=self.year,
            current_day=self.current_day,
            day_interval=self.day_interval,
            post_time=POST_TIME,
            first_year=FIRST_YEAR,
            last_day=LAST_DAY,
        )
        await ctx.send(msg)

    @commands.command()
    @commands.has_any_role("Admins", "Event Lead", "Event Runner")
    async def summer_aoc(self, ctx: commands.Context, year: int, day_interval: int, start_day: int = 1) -> None:
        """Dynamically create and start a background task to handle summer AoC."""
        if not FIRST_YEAR <= year <= 2021:
            raise commands.BadArgument(f"Year must be between {FIRST_YEAR} and 2021, inclusive")

        if not (start_day >= 1 and start_day <= LAST_DAY):
            raise commands.BadArgument(f"Start day must be between 1 and {LAST_DAY}, inclusive")

        if self.is_running:
            await ctx.send("A summer AoC event is already running!")
            return
        await ctx.send("Starting Summer AoC event...")

        self.year = year
        self.current_day = start_day
        self.day_interval = day_interval
        await self.cache.set("is_running", True)
        await self.cache.set("year", year)
        await self.cache.set("current_day", start_day)
        await self.cache.set("day_interval", day_interval)

        self.wait_task = asyncio.create_task(self.wait_until_post_time())
        await self.wait_task

        self.loop_task = tasks.Loop(
            self.post_puzzle,
            seconds=0,
            minutes=0,
            hours=(day_interval * 24),
            time=MISSING,
            count=None,
            reconnect=True,
        )
        log.info(f"Starting summer AoC event with {day_interval=}.")
        self.loop_task.start()

    @commands.command()
    @commands.has_any_role("Admins", "Event Lead", "Event Runner")
    async def stop_aoc(self, ctx: commands.Context) -> None:
        """Stops a summer AoC event if one is running."""
        if not self.is_running:
            await ctx.send("The summer AoC event is currently not running.")
            return
        await self.stop_event()
        await ctx.send("Summer AoC event stopped.")

    async def post_puzzle(self) -> None:
        """The actual coroutine that handles creating threads for summer AoC. Should be passed into task."""
        if self.current_day > LAST_DAY:
            log.info(f"Attempted to post puzzle after last day, stopping event")
            await self.stop_event()
            return

        log.info(f"Posting puzzle for day {self.current_day}")
        channel: discord.TextChannel = self.bot.get_channel(constants.Channels.aoc_main_channel)
        link = AOC_URL.format(year=self.year, day=self.current_day)
        thread_starter = await channel.send(link)  # This will be the message from which the thread will be created
        await thread_starter.create_thread(name=f"Off-season AoC #{self.current_day}")

        self.current_day += 1
        await self.cache.set("current_day", self.current_day)

    async def stop_event(self) -> None:
        """Cancel any active summer AoC tasks."""
        if self.loop_task and self.loop_task.is_running():
            self.loop_task.cancel()  # .cancel() doesn't allow the current iteration to finish
            log.debug(f"Summer AoC stopped during loop task")

        if self.wait_task and not self.wait_task.done():
            self.wait_task.cancel()
            log.debug(f"Summer AoC stopped during wait task")

        await self.cache.set("is_running", False)
        log.info("Summer AoC event stopped")

    async def wait_until_post_time(self) -> asyncio.Task:
        """Wait until the post time."""
        now = arrow.get()
        post_time_today = now.replace(hour=POST_TIME, minute=0, second=0)
        delta = post_time_today - now
        sleep_for = delta % timedelta(days=1)
        log.debug(f"Waiting until {POST_TIME}:00 UTC to start summer AoC loop")
        await asyncio.sleep(sleep_for.total_seconds())


async def setup(bot: SirRobin) -> None:
    """Load the summer AoC cog."""
    await bot.add_cog(OffSeasonAoC(bot))
