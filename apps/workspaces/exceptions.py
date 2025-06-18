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


class TeamAlreadyExistsInWorkspaceError(WorkspaceError):
    """Raised when team already exists in workspace."""

    pass


class AddTeamToWorkspaceError(WorkspaceError):
    """Raised when adding team to workspace fails."""

    pass


class TeamDoesNotBelongToOrganizationError(WorkspaceError):
    """Raised when team does not belong to organization."""

    pass
