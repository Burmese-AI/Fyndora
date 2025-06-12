class OrganizationError(Exception):
    """Base exception for organization-related errors."""
    pass

class OrganizationCreationError(OrganizationError):
    """Raised when organization creation fails."""
    pass

class OrganizationPermissionError(OrganizationError):
    """Raised when user doesn't have permission for an organization operation."""
    pass 