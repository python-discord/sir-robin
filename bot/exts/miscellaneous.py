import difflib
from typing import Union

from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import BadArgument
from pydis_core.utils.logging import get_logger

from bot.bot import SirRobin

log = get_logger(__name__)

ZEN_OF_PYTHON = """\
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability is for hobgoblins.
Special cases will be met with the full force of the PSF.
Purity beats practicality.
There are no errors.
Anyone who says there are errors will be explicitly silenced.
In the face of ambiguity, remove the freedom to guess.
There is only one way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is not real because time is fake.
If the implementation is hard to explain, it's a bad idea.
If the implementation is compliant with this style guide, it is a great idea
Namespaces may contribute towards the 120 character minimum — let’s do more of those!
"""


class Miscellaneous(commands.Cog):
    """A grouping of commands that are small and have unique but unrelated usages."""

    def __init__(self, bot: SirRobin):
        self.bot = bot

    @commands.command()
    async def zen(self, ctx: commands.Context, *, search_value: Union[int, str, None] = None) -> None:
        """Display the Zen of Python in an embed."""
        embed = Embed(
            colour=Colour.og_blurple(),
            title="The Zen of Python",
            description=ZEN_OF_PYTHON
        )

        if search_value is None:
            embed.title += ", inspired by Tim Peters"
            await ctx.send(embed=embed)
            return

        zen_lines = ZEN_OF_PYTHON.splitlines()

        # handle if it's an index int
        if isinstance(search_value, int):
            upper_bound = len(zen_lines) - 1
            lower_bound = -1 * len(zen_lines)
            if not (lower_bound <= search_value <= upper_bound):
                raise BadArgument(f"Please provide an index between {lower_bound} and {upper_bound}.")

            embed.title += f" (line {search_value % len(zen_lines)}):"
            embed.description = zen_lines[search_value]
            await ctx.send(embed=embed)
            return

        # Try to handle first exact word due difflib.SequenceMatched may use some other similar word instead
        # exact word.
        for i, line in enumerate(zen_lines):
            for word in line.split():
                if word.lower() == search_value.lower():
                    embed.title += f" (line {i}):"
                    embed.description = line
                    await ctx.send(embed=embed)
                    return

        # handle if it's a search string and not exact word
        matcher = difflib.SequenceMatcher(None, search_value.lower())

        best_match = ""
        match_index = 0
        best_ratio = 0

        for index, line in enumerate(zen_lines):
            matcher.set_seq2(line.lower())

            # the match ratio needs to be adjusted because, naturally,
            # longer lines will have worse ratios than shorter lines when
            # fuzzy searching for keywords. this seems to work okay.
            adjusted_ratio = (len(line) - 5) ** 0.5 * matcher.ratio()

            if adjusted_ratio > best_ratio:
                best_ratio = adjusted_ratio
                best_match = line
                match_index = index

        if not best_match:
            raise BadArgument("I didn't get a match! Please try again with a different search term.")

        embed.title += f" (line {match_index}):"
        embed.description = best_match
        await ctx.send(embed=embed)


async def setup(bot: SirRobin) -> None:
    """Load the Miscellaneous cog."""
    await bot.add_cog(Miscellaneous(bot))
