from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.bot import SirRobin


async def setup(bot: "SirRobin") -> None:
    """Load the CodeJams cog."""
    from bot.exts.code_jams._cog import CodeJams
    await bot.add_cog(CodeJams(bot))
