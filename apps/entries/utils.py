from apps.core.permissions import OrganizationPermissions, WorkspacePermissions
from apps.core.permissions import WorkspaceTeamPermissions


def can_view_org_expense(user, organization):
    """
    Returns True if the user has the permission to view the organization expense.
    """
    return user.has_perm(OrganizationPermissions.VIEW_ORG_ENTRY, organization)


def can_add_org_expense(user, organization):
    """
    Returns True if the user has the permission to add the organization expense.
    """
    return user.has_perm(OrganizationPermissions.ADD_ORG_ENTRY, organization)


def can_update_org_expense(user, organization):
    """
    Returns True if the user has the permission to update the organization expense.
    """
    return user.has_perm(OrganizationPermissions.CHANGE_ORG_ENTRY, organization)


def can_delete_org_expense(user, organization):
    """
    Returns True if the user has the permission to delete the organization expense.
    """
    return user.has_perm(OrganizationPermissions.DELETE_ORG_ENTRY, organization)


def can_add_workspace_expense(user, workspace):
    """
    Returns True if the user has the permission to add the workspace expense.
    """
    return user.has_perm(WorkspacePermissions.ADD_WORKSPACE_ENTRY, workspace)


def can_update_workspace_expense(user, workspace):
    """
    Returns True if the user has the permission to update the workspace expense.
    """
    return user.has_perm(WorkspacePermissions.CHANGE_WORKSPACE_ENTRY, workspace)


def can_delete_workspace_expense(user, workspace):
    """
    Returns True if the user has the permission to delete the workspace expense.
    """
    return user.has_perm(WorkspacePermissions.DELETE_WORKSPACE_ENTRY, workspace)


def can_view_workspace_team_entry(user, workspace_team):
    """
    Returns True if the user has the permission to view the workspace team entry.
    """
    return user.has_perm(WorkspaceTeamPermissions.VIEW_WORKSPACE_TEAM, workspace_team)


def can_add_workspace_team_entry(user, workspace_team):
    """
    Returns True if the user has the permission to add the workspace team entry.
    """
    return user.has_perm(
        WorkspaceTeamPermissions.ADD_WORKSPACE_TEAM_ENTRY, workspace_team
    )


def can_update_workspace_team_entry(user, workspace_team):
    """
    Returns True if the user has the permission to update the workspace team entry.
    """
    return user.has_perm(
        WorkspaceTeamPermissions.CHANGE_WORKSPACE_TEAM_ENTRY, workspace_team
    )


def can_delete_workspace_team_entry(user, workspace_team):
    """
    Returns True if the user has the permission to delete the workspace team entry.
    """
    return user.has_perm(
        WorkspaceTeamPermissions.DELETE_WORKSPACE_TEAM_ENTRY, workspace_team
    )
