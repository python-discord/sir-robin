from bot.bot import SirRobin


def setup(bot: SirRobin) -> None:
    """Load the CodeJams cog."""
    from bot.exts.code_jams._cog import CodeJams

    bot.add_cog(CodeJams(bot))
