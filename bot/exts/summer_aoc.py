import logging
from typing import Literal, Optional

import arrow
import asyncio
import discord
from async_rediscache import RedisCache
from discord.ext import commands, tasks
from discord.utils import MISSING

from bot.constants import Channels, Client, Roles
from bot.bot import SirRobin
from bot.utils.time import next_time_occurence, time_until


log = logging.getLogger(__name__)

AOC_URL = "https://adventofcode.com/{year}/day/{day}"
LAST_DAY = 25
FIRST_YEAR = 2015
LAST_YEAR = arrow.get().year - 1
PUBLIC_NAME = "Revival of Code"

INFO_TEMPLATE = """
is_running: {is_running}
wait_task active: {wait_task_active}
loop_task active: {loop_task_active}

year: {year}
current_day: {current_day}
day_interval: {day_interval}

next post: {next_post}
"""

class SummerAoC(commands.Cog):
    """Cog that handles all Summer AoC functionality."""

    cache = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot
        self.wait_task: Optional[asyncio.Task] = None
        self.loop_task: Optional[tasks.Loop] = None

        self.is_running = False
        self.year: Optional[int] = None
        self.current_day: Optional[int] = None
        self.day_interval: Optional[int] = None
        self.post_time = 0

        self.bot.loop.create_task(self.load_event_state())

    def is_configured(self) -> bool:
        """Check whether all the necessary settings are configured to run the event."""
        return None not in (self.year, self.current_day, self.day_interval, self.post_time)

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Role-lock all commands in this cog."""
        return await commands.has_any_role(
            Roles.admins,
            Roles.events_lead,
            Roles.event_runner,
        ).predicate(ctx)

    @commands.group(invoke_without_command=True, name="summeraoc", aliases=["roc", "revivalofcode"])
    async def summer_aoc_group(self, ctx: commands.Context) -> None:
        """Commands for managing the Summer AoC event."""
        desc = "\n".join(
            f"*{command.help}*\n```{Client.prefix}summeraoc {command.name} {command.signature}```"
            for command in sorted(self.summer_aoc_group.walk_commands(), key=hash)
        )
        embed = discord.Embed(description=desc)
        await ctx.send(embed=embed)

    @summer_aoc_group.command(name="info")
    async def info(self, ctx: commands.Context) -> None:
        """Display info about the state of the event."""
        embed = self.get_info_embed()
        await ctx.send(embed=embed)

    @summer_aoc_group.command(name="start")
    async def start(self, ctx: commands.Context, year: int, day_interval: int, post_time: int = 0) -> None:
        """Start the Summer AoC event. To specify a starting day other than `1`, use the `force` command."""
        if not FIRST_YEAR <= year <= LAST_YEAR:
            raise commands.BadArgument(f"Year must be between {FIRST_YEAR} and {LAST_YEAR}, inclusive")

        if day_interval < 1:
            raise commands.BadArgument(f"Day interval must be at least 1")

        if not 0 <= post_time <= 23:
            raise commands.BadArgument(f"Post time must be between 0 and 23")

        if self.is_running:
            await ctx.send("A Summer AoC event is already running!")
            return
        
        self.is_running = True
        self.year = year
        self.current_day = 1
        self.day_interval = day_interval
        self.post_time = post_time
        await self.save_event_state()

        await ctx.send("Starting Summer AoC event...")
        await self.start_event()

    @summer_aoc_group.command(name="force")
    async def force_day(self, ctx: commands.Context, day: int, now: Optional[Literal["now"]] = None) -> None:
        """
        Force-set the current day of the event. Use `now` to post the puzzle immediately.
        Can be used without starting the event first as long as the necessary settings are already stored.
        """
        if not self.is_configured():
            await ctx.send(
                content="The necessary settings are not configured to start the event",
                embed=self.get_info_embed(),
            )
            return

        if not 1 <= day <= LAST_DAY:
            raise commands.BadArgument(f"Start day must be between 1 and {LAST_DAY}, inclusive")

        log.info(f"Setting the current day of Summer AoC to {day}")
        await self.stop_event()
        self.is_running = True
        self.current_day = day
        await self.save_event_state()
        if now is not None and now.lower() == "now":
            await self.post_puzzle()
        await self.start_event()

    @summer_aoc_group.command(name="stop")
    async def stop(self, ctx: commands.Context) -> None:
        """Stop the event."""
        was_running = await self.stop_event()
        if was_running:
            await ctx.send("Summer AoC event stopped")
        else:
            await ctx.send("The Summer AoC event is not currently running")

    async def load_event_state(self) -> None:
        """Check redis for the current state of the event."""
        state = await self.cache.to_dict()
        self.is_running = state.get("is_running", False)
        self.year = state.get("year")
        self.day_interval = state.get("day_interval")
        self.current_day = state.get("current_day")
        self.post_time = state.get("post_time", 0)
        log.debug(f"Loaded state: {state}")

        if self.is_running:
            if self.is_configured():
                await self.start_event()
            else:
                log.error(f"Summer AoC state incomplete, failed to start event")
                self.is_running = False
                self.save_event_state()
    
    async def save_event_state(self) -> None:
        """Save the current state in redis."""
        await self.cache.update({
            "is_running": self.is_running,
            "year": self.year,
            "current_day": self.current_day,
            "day_interval": self.day_interval,
            "post_time": self.post_time,
        })
    
    async def start_event(self) -> None:
        """Start event by recording state and creating async tasks to post puzzles."""
        log.info(f"Starting Summer AoC event with {self.year=} {self.current_day=} {self.day_interval=}")
        sleep_for = time_until(hour=self.post_time)
        self.wait_task = asyncio.create_task(asyncio.sleep(sleep_for.total_seconds()))
        log.debug(f"Waiting until {self.post_time}:00 UTC to start Summer AoC loop")
        await self.wait_task

        self.loop_task = tasks.Loop(
            self.post_puzzle,
            seconds=0,
            minutes=0,
            hours=(self.day_interval * 24),
            time=MISSING,
            count=None,
            reconnect=True,
        )
        self.loop_task.start()

    async def stop_event(self) -> bool:
        """Cancel any active Summer AoC tasks. Returns whether the event was running."""
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

    async def post_puzzle(self) -> None:
        """Create a thread for the current day's puzzle."""
        if self.current_day > LAST_DAY:
            log.info(f"Attempted to post puzzle after last day, stopping event")
            await self.stop_event()
            return

        log.info(f"Posting puzzle for day {self.current_day}")
        channel: discord.TextChannel = self.bot.get_channel(Channels.summer_aoc_main)
        link = AOC_URL.format(year=self.year, day=self.current_day)
        thread_starter = await channel.send(link)  # This will be the message from which the thread will be created
        await thread_starter.create_thread(name=f"{PUBLIC_NAME} puzzle {self.current_day}")

        self.current_day += 1
        await self.save_event_state()

    def get_info_embed(self) -> discord.Embed:
        """Generate an embed with info about the event state."""
        desc = INFO_TEMPLATE.format(
            is_running=self.is_running,
            wait_task_active=(self.wait_task is not None) and not self.wait_task.done(),
            loop_task_active=(self.loop_task is not None) and self.loop_task.is_running(),
            year=self.year,
            current_day=self.current_day,
            day_interval=self.day_interval,
            next_post=f"<t:{int(next_time_occurence(hour=self.post_time).timestamp())}>" if self.is_running else "N/A"
        )
        return discord.Embed(
            title="Summer AoC event state",
            description=desc,
        )


async def setup(bot: SirRobin) -> None:
    """Load the Summer AoC cog."""
    await bot.add_cog(SummerAoC(bot))
