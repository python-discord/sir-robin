import random
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import discord
from async_rediscache import RedisCache
from discord.ext import commands, tasks
from pydis_core.utils.logging import get_logger

from bot import constants
from bot.bot import SirRobin
from bot.utils import members
from bot.utils.decorators import in_whitelist

logger = get_logger(__name__)

ELEVATED_ROLES = (constants.Roles.admins, constants.Roles.moderation_team, constants.Roles.events_lead)

ALLOWED_COMMAND_CHANNELS = (constants.Channels.bot_commands, constants.Channels.sir_lancebot_playground,)

# Channels where the game runs.
ALLOWED_CHANNELS = (
    constants.Channels.off_topic_0,
    constants.Channels.off_topic_1,
    constants.Channels.off_topic_2,
)

LEVEL_ROLES = (
    constants.Roles.levels_crystal,
    constants.Roles.levels_level3,
    constants.Roles.levels_s_tier,
    constants.Roles.levels_diamond_rank,
    constants.Roles.levels_GOAT,
    constants.Roles.levels_mtfn,
    constants.Roles.levels_champion,
    constants.Roles.levels_mythical_python_charmer,
    constants.Roles.levels_supernova_wonder,
    constants.Roles.levels_ascenion_20
)

class Levels(commands.Cog):
    """Cog that handles all Level functionality."""

    #RedisCache[user_id: int, points: int]
    user_points_cache = RedisCache()

    #RedisCache[role_id: int, point_threshold: int]
    levels_cache = RedisCache()

    #RedisCache["value", bool]
    running = RedisCache()

    def __init__(self, bot: SirRobin):
        self.bot = bot

        self.rules_all = []
        self.rules_pool = []
        self.rules_active = []
        self.rules_folder_path = Path("./bot/exts/levels/rules/")
        self.active_rules_num = 3

        self.active_reaction_rule_triggers = []
        self.active_message_rule_triggers = []


    async def cog_load(self) -> None:
        """Run startup tasks needed when cog is first loaded."""
        await self._load_rules()

        # Fill in cache with data for later functions to use
        if await self.levels_cache.length() == 0:
            shuffled_roles = random.sample(LEVEL_ROLES, len(LEVEL_ROLES))
            init_threshold_dict = dict.fromkeys(shuffled_roles, 0)
            await self.levels_cache.update(init_threshold_dict)
        logger.info("Filled levels cache with initial thresholds")

        if await self.running.get("value", False):
            logger.debug("Starting Rules and Point Renormalization tasks")
            self._cycle_rules_task.start()
            logger.info("Started rule cycle task")
            self._calculate_point_thresholds_task.start()
            logger.info("Started point threshold task")

    async def _load_rules(self) -> None:
        """
        Load and parse levels rules for usage.

        If a rule file does not comply with the format
        and throws and error, it is skipped over.
        """
        total_files_loaded = 0
        for toml_file in self.rules_folder_path.glob("*.toml"):
            with open(toml_file, "rb") as f:
                rule_dict = tomllib.load(f)

            rule_name = toml_file.stem
            try:
                rule_triggers = [RuleTrigger(**rule_trigger) for rule_trigger in rule_dict["rule"]]
                rule = LevelRules(rule_name, rule_triggers)
            except (TypeError, KeyError):
                logger.info(f"{toml_file} not properly formatted, skipping.")
                continue

            self.rules_all.append(rule)
            total_files_loaded += 1

        logger.info(f"Total rules loaded: {total_files_loaded}")

    @tasks.loop(minutes=42.0)
    async def _cycle_rules_task(self) -> None:
        """
        Change which rules are currently active.

        Rules will statistically be used before a repeat is seen.
        This is not a guarnatee though.
        """
        if len(self.rules_pool) < self.active_rules_num:
            # If pool is empty, reshuffle completely to avoid activating same rule twice
            self.rules_pool = random.sample(self.rules_all, len(self.rules_all))
        self.rules_active = [self.rules_pool.pop() for _ in range(self.active_rules_num)]
        logger.debug(f"Cycled active rules to: {[rule.name for rule in self.rules_active]}")


        self.active_message_rule_triggers = [
            rule_trigger for rule in self.rules_active
            for rule_trigger in rule.rule_triggers if rule_trigger.interaction_type=="message"
        ]
        self.active_reaction_rule_triggers = [
            rule_trigger for rule in self.rules_active
            for rule_trigger in rule.rule_triggers if rule_trigger.interaction_type=="reaction"
        ]
        # [rule for rule in self.rules_active if rule.interaction_type=="reaction"]
        # self.active_message_rule_triggers = [rule for rule in self.rules_active if rule.interaction_type=="message"]

    @tasks.loop(minutes=90.0)
    async def _calculate_point_thresholds_task(self) -> None:
        """
        Calculate point thresholds based on number of roles, aiming for even deciles based on scores.

        If current max score is less than 100, it will fix deciles to increments of 10.
        """
        user_points = await self.user_points_cache.to_dict()
        all_scores = sorted(user_points.values())
        if all_scores and all_scores[-1] >= 100:
            num_scores = len(all_scores)
            num_levels = len(LEVEL_ROLES)
            thresholds = [
                all_scores[round(num_scores * level/num_levels)]
                for level in range(1, num_levels+1)
            ]
        else:
            # At the start of the event, just use multiples of 10 up to 100
            thresholds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        levels = await self.levels_cache.to_dict()
        new_levels = dict(zip(levels.keys(), thresholds, strict=False))
        await self.levels_cache.update(new_levels)
        logger.debug(f"Renormalizing score thresholds. Total scores: {len(all_scores)}")
        logger.debug(f"New thresholds: {thresholds}")


    async def _update_points(self, user_id: int, points: int) -> None:
        """Updates user's score and ensures correct role is assigned."""
        logger.debug(f"User {user_id} getting {points} points.")
        if not await self.user_points_cache.contains(user_id):
            await self.user_points_cache.set(user_id, points)
        else:
            if points == 0:
                return

            current_points = await self.user_points_cache.get(user_id)
            new_point_total = current_points + points
            await self.user_points_cache.set(user_id, new_point_total)

        await self._update_role_assignment(user_id)


    async def _update_role_assignment(self, user_id: int) -> None:
        """Updates user's role based on current points and role-point thresholds."""
        user_points = await self.user_points_cache.get(user_id)
        levels = await self.levels_cache.to_dict()
        level_to_assign = None

        for role, point_threshold in sorted(levels.items(), key=lambda item: item[1]):
            level_to_assign = role
            if point_threshold >= user_points:
                break

        guild = self.bot.get_guild(constants.Bot.guild)
        role = guild.get_role(level_to_assign)
        user = await members.get_or_fetch_member(guild, user_id)
        if role in user.roles:
            return
        logger.debug(f"Assigning {role.name} to {user.name}")
        await members.handle_role_change(user, user.add_roles, role)


    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """Listens to messages and checks against active message rules."""
        if not await self.running.get("value", False):
            return
        if msg.channel.id not in ALLOWED_CHANNELS or msg.author.bot:
            return
        if len(self.active_message_rule_triggers) == 0:
            return

        total_points = 0
        rule_matches = 0
        for rule_trigger in self.active_message_rule_triggers:
            re_pattern = rule_trigger.message_content
            match = re.search(re_pattern, msg.content)
            if match:
                total_points += rule_trigger.points
                rule_matches += 1

        # Only update points if they've matched any rules
        # If they match multiple rules and earn 0 points,
        # that should still get them a role
        if rule_matches != 0:
            user_id = msg.author.id
            await self._update_points(user_id, total_points)
        elif rule_matches >= 3:
            user_id = msg.author.id
            total_points -= 5
            await self._update_points(user_id, total_points)


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member) -> None:
        """
        Listens for reactions and checks for against active reaction rules.

        It will only listen for reactions added to messages within the bot's message cache.
        """
        if not await self.running.get("value", False):
            return
        if reaction.message.channel.id not in ALLOWED_CHANNELS or user.bot:
            return
        if len(self.active_reaction_rule_triggers) == 0:
            return

        if isinstance(reaction.emoji, str):
            emoji_name = reaction.emoji
        else:
            emoji_name = reaction.emoji.name

        total_points = 0
        rule_matches = 0
        for rule_trigger in self.active_reaction_rule_triggers:
            if emoji_name in rule_trigger.reaction_content:
                total_points += rule_trigger.points
                rule_matches += 1

        # Only update points if they've matched any rules
        # If they match multiple rules and earn 0 points,
        # that should still get them a role
        if rule_matches != 0:
            await self._update_points(user.id, total_points)


    @commands.group(name="levels")
    async def levels_command_group(self, ctx: commands.Context) -> None:
        """Levels group command."""
        if not ctx.invoked_subcommand:
            await self.bot.invoke_help_command(ctx)


    @levels_command_group.command()
    @in_whitelist(channels=ALLOWED_COMMAND_CHANNELS)
    async def points(self, ctx: commands.Context) -> None:
        """Check how many points you've accrued for the Role Level system."""
        user_id = ctx.author.id

        if await self.user_points_cache.contains(user_id):
            points = await self.user_points_cache.get(user_id)
            await ctx.reply(f"You have {points} points.")
        else:
            await ctx.reply("You have not earned any points so far! :D")


    @levels_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def shuffle_role_order(self, ctx: commands.Context) -> None:
        """Shuffle which roles are assigned to which point thresholds."""
        levels = await self.levels_cache.to_dict()
        thresholds = levels.values()

        role_order = random.sample(LEVEL_ROLES, len(LEVEL_ROLES))
        updated_ordering = dict(zip(role_order, thresholds, strict=False))

        await self.levels_cache.update(updated_ordering)
        logger.info(f"Roles have been re-shuffled per request of {ctx.author.name}")

    @levels_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def start(self, ctx: commands.Context) -> None:
        """Allows Levels to run, check messages, and assign roles."""
        current_state = await self.running.get("value", False)
        if current_state:
            await ctx.reply("Levels is already running.")
            return

        self._cycle_rules_task.start()
        self._calculate_point_thresholds_task.start()
        await self.running.set("value", True)
        await ctx.reply("Levels is now turned on.")

    @levels_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def stop(self, ctx: commands.Context) -> None:
        """Disallows Levels to run, check messages, and assign roles."""
        current_state = await self.running.get("value", False)
        if not current_state:
            await ctx.reply("Levels is already off.")
            return

        self._cycle_rules_task.cancel()
        self._calculate_point_thresholds_task.cancel()
        await self.running.set("value", False)
        await ctx.reply("Levels is now turned off.")

    @levels_command_group.command()
    @commands.has_any_role(*ELEVATED_ROLES)
    async def status(self, ctx: commands.Context) -> None:
        """Replies with current status of Levels."""
        current_state = await self.running.get("value", False)
        if current_state:
            await ctx.reply(":white_check_mark: Levels is currently running.")
        else:
            await ctx.reply(":x: Levels is current **not** running.")


# Please see ./rules/README.md for how to format rules

@dataclass
class RuleTrigger:
    interaction_type: Literal["message", "reaction"]
    reaction_content: list[str] | None = None
    message_content: str | None = None
    points: int = 0

@dataclass
class LevelRules:
    name: str
    rule_triggers: list[RuleTrigger]
