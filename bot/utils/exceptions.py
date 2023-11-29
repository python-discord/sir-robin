from collections.abc import Container

from discord.ext.commands import CheckFailure


class JamCategoryNameConflictError(Exception):
    """Raised when upon creating a CodeJam the main jam category and the teams' category conflict."""


class CodeJamCategoryCheckFailure(CheckFailure):
    """Raised when the specified command was run outside the Code Jam categories."""


class InMonthCheckFailure(CheckFailure):
    """Check failure for when a command is invoked outside of its allowed month."""


class SilentChannelFailure(CheckFailure):
    """Raised when someone should not use a command in a context and should silently fail."""


class InWhitelistCheckFailure(CheckFailure):
    """Raised when the `in_whitelist` check fails."""

    def __init__(self, redirect_channels: Container[int] | None):
        self.redirect_channels = redirect_channels

        if redirect_channels:
            channels = ">, <#".join([str(channel) for channel in redirect_channels])
            redirect_message = f" here. Please use the <#{channels}> channel(s) instead"
        else:
            redirect_message = ""

        error_message = f"You are not allowed to use that command{redirect_message}."

        super().__init__(error_message)
