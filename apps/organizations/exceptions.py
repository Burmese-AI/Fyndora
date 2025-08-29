class OrganizationError(Exception):
    """Base exception for organization-related errors."""

    pass


class OrganizationCreationError(OrganizationError):
    """Raised when organization creation fails."""

    pass


class OrganizationPermissionError(OrganizationError):
    """Raised when user doesn't have permission for an organization operation."""

    pass


class OrganizationUpdateError(OrganizationError):
    """Raised when organization update fails."""

    pass


class OrganizationPermissionCreationError(OrganizationError):
    """Raised when organization permission creation fails."""

    pass


class OrganizationMemberPermissionError(OrganizationError):
    """Raised when organization member permission fails."""

    pass


class OrganizationMemberPermissionCreationError(OrganizationError):
    """Raised when organization member permission creation fails."""

    pass
