from discord.ext.commands import CheckFailure


class JamCategoryNameConflictError(Exception):
    """Raised when upon creating a CodeJam the main jam category and the teams' category conflict."""

    pass


class CodeJamCategoryCheckFailure(CheckFailure):
    """Raised when the specified command was run outside the Code Jam categories."""

    pass
