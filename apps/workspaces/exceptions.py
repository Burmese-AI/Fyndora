class WorkspaceError(Exception):
    """Base exception for workspace-related errors."""

    pass


class WorkspaceCreationError(WorkspaceError):
    """Raised when workspace creation fails."""

    pass


class WorkspacePermissionError(WorkspaceError):
    """Raised when user doesn't have permission for a workspace operation."""

    pass


class WorkspaceUpdateError(WorkspaceError):
    """Raised when workspace update fails."""

    pass
