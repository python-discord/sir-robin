import asyncio
import logging
from datetime import timedelta
from typing import Literal, Optional

import arrow
import discord
from async_rediscache import RedisCache
from discord.ext import commands, tasks
from discord.utils import MISSING

from bot.bot import SirRobin
from bot.constants import Channels, Client, Roles
from bot.utils.time import time_until

log = logging.getLogger(__name__)

AOC_URL = "https://adventofcode.com/{year}/day/{day}"
LAST_DAY = 25
FIRST_YEAR = 2015
LAST_YEAR = arrow.get().year - 1
PUBLIC_NAME = "Revival of Code"
REAL_AOC_START = f"{arrow.get().year}-12-01T05:00:00"

INFO_TEMPLATE = """
is_running: {is_running}
year: {year}
current_day: {current_day}
day_interval: {day_interval}
first_post: {first_post}
next post: {next_post}
"""

POST_TEXT = """
The next puzzle in our {public_name} is now released!

We're revisiting an old Advent of Code event at a slower pace. To participate, check out the linked puzzle\
 then come join us in this thread when you've solved it or need help!

*Please remember to keep all solution spoilers for this puzzle in the thread.*
If you have questions or suggestions about the event itself, head over to <#{discussion}>.
{next_puzzle_text}
"""

NEXT_PUZZLE_TEXT = """
The next puzzle will be posted <t:{timestamp}:R>.
To receive notifications when new puzzles are released, run `!subscribe` in <#{bot_commands}> and assign yourself \
the Revival of Code role.
"""

LAST_PUZZLE_TEXT = """
This is the last puzzle! ||...until Advent of Code starts <t:{timestamp}:R>!||
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
        self.first_post_date: Optional[arrow.Arrow] = None

        self.bot.loop.create_task(self.load_event_state())

    def is_configured(self) -> bool:
        """Check whether all the necessary settings are configured to run the event."""
        return None not in (self.year, self.current_day, self.day_interval, self.post_time)

    def next_post_time(self) -> Optional[arrow.Arrow]:
        """Calculate the datetime of the next scheduled post."""
        now = arrow.get()
        if self.first_post_date is None:
            delta = time_until(hour=self.post_time)
        else:
            since_start = now - self.first_post_date
            day_interval = timedelta(days=self.day_interval)
            delta = day_interval - (since_start % day_interval)
        return now + delta

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Role-lock all commands in this cog."""
        return await commands.has_any_role(
            Roles.admins,
            Roles.events_lead,
            Roles.event_runner,
        ).predicate(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Send help text on user input error."""
        if isinstance(error, commands.UserInputError):
            desc = f"```{Client.prefix}summeraoc {ctx.command.name} {ctx.command.signature}```"
            embed = discord.Embed(
                description=desc,
            )
            await ctx.send(embed=embed)

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
        """
        Start the Summer AoC event.
        To specify a starting day other than `1`, use the `force` command.

        `year` must be an integer at least 2015.
        `day_interval` must be an integer at least 1.
        `post_time` must be an integer between 0 and 23.
        """  # noqa: D205
        if not FIRST_YEAR <= year <= LAST_YEAR:
            raise commands.BadArgument(f"Year must be between {FIRST_YEAR} and {LAST_YEAR}, inclusive")

        if day_interval < 1:
            raise commands.BadArgument("Day interval must be at least 1")

        if not 0 <= post_time <= 23:
            raise commands.BadArgument("Post time must be between 0 and 23")

        if self.is_running:
            await ctx.send("A Summer AoC event is already running!")
            return

        self.is_running = True
        self.year = year
        self.current_day = 1
        self.day_interval = day_interval
        self.post_time = post_time
        await self.save_event_state()

        embed = self.get_info_embed()
        embed.color = discord.Color.green()
        embed.title = "Event started!"
        await ctx.send(embed=embed)

        await self.start_event()

    @summer_aoc_group.command(name="force")
    async def force_day(self, ctx: commands.Context, day: int, now: Optional[Literal["now"]] = None) -> None:
        """
        Force-set the current day of the event. Use `now` to post the puzzle immediately.
        Can be used without starting the event first as long as the necessary settings are already stored.
        Does not reset the starting day (i.e. won't change the day cycle), but will set it if it's not already set.
        """  # noqa: D205
        if now is not None and now.lower() != "now":
            raise commands.BadArgument(f"Unrecognized option: {now}")

        if not self.is_configured():
            embed = self.get_info_embed()
            embed.title = "The necessary settings are not configured to start the event"
            embed.color = discord.Color.red()
            await ctx.send(embed=embed)
            return

        if not 1 <= day <= LAST_DAY:
            raise commands.BadArgument(f"Start day must be between 1 and {LAST_DAY}, inclusive")

        log.info(f"Setting the current day of Summer AoC to {day}")
        await self.stop_event()
        self.is_running = True
        self.current_day = day
        await self.save_event_state()
        if now:
            await self.post_puzzle()

        embed = self.get_info_embed()
        title = "Event is now running"
        if now:
            title = "Puzzle posted and event is now running"
        embed.title = title
        embed.color = discord.Color.green()
        await ctx.send(embed=embed)
        await self.start_event()

    @summer_aoc_group.command(name="stop")
    async def stop(self, ctx: commands.Context) -> None:
        """Stop the event."""
        self.first_post_date = None  # Clean up; the start date should be reset when the event is started.
        self.save_event_state()
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
        first_post_date = state.get("first_post_date")
        if first_post_date is not None:
            first_post_date = arrow.get(first_post_date)
        self.first_post_date = first_post_date
        log.debug(f"Loaded state: {state}")

        if self.is_running:
            if self.is_configured():
                await self.start_event()
            else:
                log.error("Summer AoC state incomplete, failed to start event")
                self.is_running = False
                self.save_event_state()

    async def save_event_state(self) -> None:
        """Save the current state in redis."""
        state = {
            "is_running": self.is_running,
            "year": self.year,
            "current_day": self.current_day,
            "day_interval": self.day_interval,
            "post_time": self.post_time,
        }
        if self.first_post_date is not None:
            state["first_post_date"] = self.first_post_date.isoformat()
        await self.cache.update(state)

    async def start_event(self) -> None:
        """Start event by recording state and creating async tasks to post puzzles."""
        log.info(f"Starting Summer AoC event with {self.year=} {self.current_day=} {self.day_interval=}")

        sleep_for = self.next_post_time() - arrow.get()
        self.wait_task = asyncio.create_task(asyncio.sleep(sleep_for.total_seconds()))
        log.debug(f"Waiting until {self.post_time}:00 UTC to start Summer AoC loop")
        await self.wait_task

        if self.first_post_date is None:
            self.first_post_date = arrow.get()

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
            log.error("Both wait and loop tasks were active. Both should now be cancelled.")

        if was_waiting:
            self.wait_task.cancel()
            log.debug("Summer AoC stopped during wait task")

        if was_looping:
            self.loop_task.cancel()  # .cancel() doesn't allow the current iteration to finish
            log.debug("Summer AoC stopped during loop task")

        self.is_running = False
        await self.save_event_state()
        log.info("Summer AoC event stopped")
        return was_waiting or was_looping

    async def post_puzzle(self) -> None:
        """Create a thread for the current day's puzzle."""
        if self.current_day > LAST_DAY:
            log.error("Attempted to post puzzle after last day, stopping event")
            await self.stop_event()
            return

        log.info(f"Posting puzzle for day {self.current_day}")
        channel: discord.TextChannel = self.bot.get_channel(Channels.summer_aoc_main)
        thread_starter = await channel.send(
            f"<@&{Roles.summer_aoc}>",
            embed=self.get_puzzle_embed(),
        )
        await thread_starter.create_thread(name=f"Day {self.current_day} Spoilers")

        self.current_day += 1
        await self.save_event_state()
        if self.current_day > LAST_DAY:
            await self.stop_event()

    def get_info_embed(self) -> discord.Embed:
        """Generate an embed with info about the event state."""
        desc = INFO_TEMPLATE.format(
            is_running=self.is_running,
            year=self.year,
            current_day=self.current_day,
            day_interval=self.day_interval,
            first_post=f"<t:{int(self.first_post_date.timestamp())}>" if self.first_post_date else "N/A",
            next_post=f"<t:{int(self.next_post_time().timestamp())}>" if self.is_running else "N/A",
        )
        return discord.Embed(
            title="Summer AoC event state",
            description=desc,
        )

    def get_puzzle_embed(self) -> discord.Embed:
        """Generate an embed for the day's puzzle post."""
        if self.current_day == LAST_DAY:
            next_puzzle_text = LAST_PUZZLE_TEXT.format(timestamp=int(arrow.get(REAL_AOC_START).timestamp()))
        else:
            next_puzzle_text = NEXT_PUZZLE_TEXT.format(
                timestamp=int(self.next_post_time().timestamp()),
                bot_commands=Channels.bot_commands,
            )
        post_text = POST_TEXT.format(
            public_name=PUBLIC_NAME,
            discussion=Channels.summer_aoc_discussion,
            next_puzzle_text=next_puzzle_text,
        )

        embed = discord.Embed(
            title=f"**Day {self.current_day}  (puzzle link)**",
            url=AOC_URL.format(year=self.year, day=self.current_day),
            description=post_text,
            color=discord.Color.yellow(),
        )
        return embed


async def setup(bot: SirRobin) -> None:
    """Load the Summer AoC cog."""
    await bot.add_cog(SummerAoC(bot))
