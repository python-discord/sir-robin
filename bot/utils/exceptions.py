from discord.ext.commands import CheckFailure


class JamCategoryNameConflictError(Exception):
    """Raised when upon creating a CodeJam the main jam category and the teams' category conflict."""



class CodeJamCategoryCheckFailure(CheckFailure):
    """Raised when the specified command was run outside the Code Jam categories."""



class MovedCommandError(Exception):
    """Raised when a command has moved locations."""

    def __init__(self, new_command_name: str):
        self.new_command_name = new_command_name
