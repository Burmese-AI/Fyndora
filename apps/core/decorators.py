import functools

from apps.core.services.permissions import check_permission


def require_permissions(permissions):
    """
    Decorator for service functions that checks if the user has all required permissions.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user and context from kwargs
            user = kwargs.get("user")
            workspace = kwargs.get("workspace")
            team = kwargs.get("team")

            if not user:
                raise ValueError("User parameter is required for permission checks")

            # Check all permissions
            for permission in permissions:
                check_permission(
                    user=user, permission=permission, workspace=workspace, team=team
                )

            # If all permission checks pass, execute the function
            return func(*args, **kwargs)

        return wrapper

    return decorator
