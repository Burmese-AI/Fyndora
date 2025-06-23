class TeamError(Exception):
    """ Base exception"""
    pass

class TeamCreationError(TeamError):
    """Raised when team creation fails."""

    pass