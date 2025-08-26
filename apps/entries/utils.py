from apps.core.permissions import (
    OrganizationPermissions,
    WorkspacePermissions,
    WorkspaceTeamPermissions,
    EntryPermissions,
)


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


def can_update_other_submitters_entry(user, org_member, entry, workspace_team):
    """
    Returns True if the user has the permission to update other submitters entry.

    """
    if not user.has_perm(
        EntryPermissions.CHANGE_OTHER_SUBMITTERS_ENTRY, entry
    ) and not own_higher_admin_role(org_member, workspace_team):
        return False
    return True


def can_delete_workspace_team_entry(user, workspace_team):
    """
    Returns True if the user has the permission to delete the workspace team entry.
    """
    return user.has_perm(
        WorkspaceTeamPermissions.DELETE_WORKSPACE_TEAM_ENTRY, workspace_team
    )


def extract_entry_business_context(entry):
    """
    Extract business context from an entry for audit logging.
    """
    if not entry:
        return {}

    return {
        "entry_id": str(entry.entry_id),
        "entry_type": entry.entry_type,
        "workspace_id": str(entry.workspace.workspace_id),
        "workspace_name": entry.workspace.title,
        "organization_id": str(entry.workspace.organization.organization_id),
    }


def own_higher_admin_role(user, workspace_team):
    """
    Returns True if the user has admin role.
    """
    is_team_coordinator = user == workspace_team.team.team_coordinator
    is_workspace_admin = user == workspace_team.workspace.workspace_admin
    is_operation_reviewer = user == workspace_team.workspace.operations_reviewer
    is_org_admin = user == workspace_team.workspace.organization.owner

    # if one condition is true, return True
    return (
        is_team_coordinator
        or is_workspace_admin
        or is_operation_reviewer
        or is_org_admin
    )


def can_view_total_workspace_teams_entries(user, workspace):
    """
    Returns True if the user has the permission to view the total workspace teams entries.
    """
    return user.has_perm(
        WorkspacePermissions.VIEW_TOTAL_WORKSPACE_TEAMS_ENTRIES, workspace
    )


def can_view_workspace_level_entries(user, workspace):
    """
    Returns True if the user has the permission to view the workspace level entries.
    """
    return user.has_perm(WorkspacePermissions.VIEW_WORKSPACE_ENTRY, workspace)
