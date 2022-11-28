from bot.bot import SirRobin


async def setup(bot: SirRobin) -> None:
    """Set up the Advent of Code extension."""
    # Import the Cog at runtime to prevent side effects like defining
    # RedisCache instances too early.
    from ._cog import AdventOfCode

    await bot.add_cog(AdventOfCode(bot))
