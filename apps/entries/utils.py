from apps.core.permissions import OrganizationPermissions, WorkspacePermissions


def user_has_organization_permission(user, permission, organization):
    """
    Helper function to check if user has organization permission.
    """
    if not user or not organization:
        return False
    try:
        return user.has_perm(permission, organization)
    except Exception:
        return False


def user_has_workspace_permission(user, permission, workspace):
    """
    Helper function to check if user has workspace permission.
    """
    if not user or not workspace:
        return False
    try:
        return user.has_perm(permission, workspace)
    except Exception:
        return False


def can_view_org_expense(user, organization):
    """
    Returns True if the user has the permission to view the organization expense.
    """
    try:
        return user_has_organization_permission(user, OrganizationPermissions.VIEW_ORG_ENTRY, organization)
    except Exception:
        return False


def can_add_org_expense(user, organization):
    """
    Returns True if the user has the permission to add the organization expense.
    """
    try:
        return user_has_organization_permission(user, OrganizationPermissions.ADD_ORG_ENTRY, organization)
    except Exception:
        return False


def can_update_org_expense(user, organization):
    """
    Returns True if the user has the permission to update the organization expense.
    """
    try:
        return user_has_organization_permission(user, OrganizationPermissions.CHANGE_ORG_ENTRY, organization)
    except Exception:
        return False


def can_delete_org_expense(user, organization):
    """
    Returns True if the user has the permission to delete the organization expense.
    """
    try:
        return user_has_organization_permission(user, OrganizationPermissions.DELETE_ORG_ENTRY, organization)
    except Exception:
        return False


def can_add_workspace_expense(user, workspace):
    """
    Returns True if the user has the permission to add the workspace expense.
    """
    try:
        return user_has_workspace_permission(user, WorkspacePermissions.ADD_WORKSPACE_ENTRY, workspace)
    except Exception:
        return False


def can_update_workspace_expense(user, workspace):
    """
    Returns True if the user has the permission to update the workspace expense.
    """
    try:
        return user_has_workspace_permission(user, WorkspacePermissions.CHANGE_WORKSPACE_ENTRY, workspace)
    except Exception:
        return False


def can_delete_workspace_expense(user, workspace):
    """
    Returns True if the user has the permission to delete the workspace expense.
    """
    try:
        return user_has_workspace_permission(user, WorkspacePermissions.DELETE_WORKSPACE_ENTRY, workspace)
    except Exception:
        return False
