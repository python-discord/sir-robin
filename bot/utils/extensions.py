from discord.ext.commands import Context


async def invoke_help_command(ctx: Context) -> None:
    """Invoke the help command or default help command if help extensions is not loaded."""
    if "bot.exts.core.help" in ctx.bot.extensions:
        help_command = ctx.bot.get_command("help")
        await ctx.invoke(help_command, ctx.command.qualified_name)
        return
    await ctx.send_help(ctx.command)
