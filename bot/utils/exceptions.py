from discord.ext.commands.errors import CheckFailure


class InIntervalCheckFailure(CheckFailure):
    """Check failure for when a command is invoked outside of its allowed month."""

    pass


class MalformedSeasonLockConfigError(Exception):
    """Thrown when an invalid or malformed config is provided."""

    pass


class UserNotPlayingError(Exception):
    """Raised when users try to use game commands when they are not playing."""

    pass


class MovedCommandError(Exception):
    """Raised when a command has moved locations."""

    def __init__(self, new_command_name: str):
        self.new_command_name = new_command_name
