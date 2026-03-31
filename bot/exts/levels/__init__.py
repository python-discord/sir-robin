from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.bot import SirRobin


async def setup(bot: "SirRobin") -> None:
    """Load the CodeJams cog."""
    from bot.exts.levels._cog import Levels
    await bot.add_cog(Levels(bot))
