import logging
from typing import Optional

import arrow
import asyncio
import discord
from async_rediscache import RedisCache
from datetime import timedelta
from discord.ext import commands, tasks
from discord.utils import MISSING

from bot.constants import Channels, Roles
from bot.bot import SirRobin


log = logging.getLogger(__name__)

AOC_URL = "https://adventofcode.com/{year}/day/{day}"
LAST_DAY = 25
FIRST_YEAR = 2015
POST_TIME = 5  # UTC
LAST_YEAR = arrow.get().year - 1


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

        self.is_running = False
        self.year: Optional[int] = None
        self.current_day: Optional[int] = None
        self.day_interval: Optional[int] = None

        self.bot.loop.create_task(self.load_event_state())

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Role-lock all commands in this cog."""
        return await commands.has_any_role(
            Roles.admins,
            Roles.events_lead,
            Roles.event_runner,
        ).predicate(ctx)

    @commands.group(invoke_without_command=True, name="summeraoc")
    async def summer_aoc_group(self, ctx: commands.Context):
        """Commands for running the Summer AoC event"""
        await ctx.send_help(ctx.command)

    @summer_aoc_group.command(name="info")
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

    @summer_aoc_group.command(name="start")
    async def start(self, ctx: commands.Context, year: int, day_interval: int, start_day: int = 1) -> None:
        """Dynamically create and start a background task to handle summer AoC."""
        if not FIRST_YEAR <= year <= LAST_YEAR:
            raise commands.BadArgument(f"Year must be between {FIRST_YEAR} and {LAST_YEAR}, inclusive")

        if not (start_day >= 1 and start_day <= LAST_DAY):
            raise commands.BadArgument(f"Start day must be between 1 and {LAST_DAY}, inclusive")

        if self.is_running:
            await ctx.send("A summer AoC event is already running!")
            return

        await ctx.send("Starting Summer AoC event...")
        await self.start_event(year, day_interval, start_day)

    @summer_aoc_group.command(name="stop")
    async def stop(self, ctx: commands.Context) -> None:
        """Stops a summer AoC event if one is running."""
        was_running = await self.stop_event()
        if was_running:
            await ctx.send("Summer AoC event stopped")
        else:
            await ctx.send("The summer AoC event is not currently running")

    async def load_event_state(self) -> None:
        """Check redis for the current state of the event."""
        state = await self.cache.to_dict()
        log.debug(f"Loaded state: {state}")
        if state.get("is_running"):
            if not all(key in state for key in ("year", "current_day", "day_interval")):
                log.error(f"Summer AoC state incomplete, failed to load")
                return
            await self.start_event(state["year"], state["day_interval"], state["current_day"])
    
    async def save_event_state(self) -> None:
        """Save the current state in redis."""
        await self.cache.update({
            "is_running": self.is_running,
            "year": self.year,
            "current_day": self.current_day,
            "day_interval": self.day_interval,
        })
    
    async def start_event(self, year: int, day_interval: int, start_day: int) -> None:
        """Start event by recording state and creating async tasks to post puzzles."""
        self.is_running = True
        self.year = year
        self.current_day = start_day
        self.day_interval = day_interval
        await self.save_event_state()

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
        log.info(f"Starting summer AoC event with {year=} {start_day=} {day_interval=}")
        self.loop_task.start()

    async def stop_event(self) -> bool:
        """Cancel any active summer AoC tasks. Returns whether the event was running."""
        was_waiting = self.wait_task and not self.wait_task.done()
        was_looping = self.loop_task and self.loop_task.is_running()
        if was_waiting and was_looping:
            log.error(f"Both wait and loop tasks were active. Both should now be cancelled.")

        if was_waiting:
            self.wait_task.cancel()
            log.debug(f"Summer AoC stopped during wait task")

        if was_looping:
            self.loop_task.cancel()  # .cancel() doesn't allow the current iteration to finish
            log.debug(f"Summer AoC stopped during loop task")

        self.is_running = False
        await self.save_event_state()
        log.info("Summer AoC event stopped")
        return was_waiting or was_looping

    async def wait_until_post_time(self) -> asyncio.Task:
        """Wait until the post time."""
        now = arrow.get()
        post_time_today = now.replace(hour=POST_TIME, minute=0, second=0)
        delta = post_time_today - now
        sleep_for = delta % timedelta(days=1)
        log.debug(f"Waiting until {POST_TIME}:00 UTC to start summer AoC loop")
        await asyncio.sleep(sleep_for.total_seconds())

    async def post_puzzle(self) -> None:
        """The actual coroutine that handles creating threads for summer AoC. Should be passed into task."""
        if self.current_day > LAST_DAY:
            log.info(f"Attempted to post puzzle after last day, stopping event")
            await self.stop_event()
            return

        log.info(f"Posting puzzle for day {self.current_day}")
        channel: discord.TextChannel = self.bot.get_channel(Channels.aoc_main_channel)
        link = AOC_URL.format(year=self.year, day=self.current_day)
        thread_starter = await channel.send(link)  # This will be the message from which the thread will be created
        await thread_starter.create_thread(name=f"Off-season AoC #{self.current_day}")

        self.current_day += 1
        await self.save_event_state()


async def setup(bot: SirRobin) -> None:
    """Load the summer AoC cog."""
    await bot.add_cog(OffSeasonAoC(bot))
