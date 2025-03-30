from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.bot import SirRobin


async def setup(bot: "SirRobin") -> None:
    """Load the CodeJams cog."""
    from bot.exts.smart_eval._cog import SmartEval
    await bot.add_cog(SmartEval(bot))
