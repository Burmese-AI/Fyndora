from apps.core.permissions import (
    OrganizationPermissions,
    WorkspacePermissions,
    TeamPermissions,
)


ROLES = {
    "ORG_OWNER": [
        OrganizationPermissions.MANAGE_ORGANIZATION,
        OrganizationPermissions.CHANGE_ORGANIZATION,
        OrganizationPermissions.DELETE_ORGANIZATION,
        OrganizationPermissions.VIEW_ORGANIZATION,
        OrganizationPermissions.ADD_WORKSPACE,
        OrganizationPermissions.ADD_TEAM,
        OrganizationPermissions.INVITE_ORG_MEMBER,
        OrganizationPermissions.ADD_ORG_ENTRY,
        OrganizationPermissions.VIEW_ORG_ENTRY,
        OrganizationPermissions.CHANGE_ORG_ENTRY,
        OrganizationPermissions.DELETE_ORG_ENTRY,
        OrganizationPermissions.CHANGE_WORKSPACE_ADMIN,
        OrganizationPermissions.CHANGE_TEAM_COORDINATOR,
        OrganizationPermissions.ADD_ORG_CURRENCY,
        OrganizationPermissions.CHANGE_ORG_CURRENCY,
        OrganizationPermissions.DELETE_ORG_CURRENCY,
        WorkspacePermissions.CHANGE_WORKSPACE_CURRENCY,
        WorkspacePermissions.DELETE_WORKSPACE_CURRENCY,
    ],
    "WORKSPACE_ADMIN": [
        OrganizationPermissions.MANAGE_ORGANIZATION,
        OrganizationPermissions.ADD_TEAM,
        WorkspacePermissions.CHANGE_WORKSPACE,
        WorkspacePermissions.DELETE_WORKSPACE,
        WorkspacePermissions.VIEW_WORKSPACE,
        WorkspacePermissions.ASSIGN_TEAMS,
        WorkspacePermissions.LOCK_WORKSPACE,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.EXPORT_WORKSPACE_REPORT,
        WorkspacePermissions.ADD_WORKSPACE_ENTRY,
        WorkspacePermissions.CHANGE_WORKSPACE_ENTRY,
        WorkspacePermissions.DELETE_WORKSPACE_ENTRY,
        WorkspacePermissions.VIEW_WORKSPACE_ENTRY,
        WorkspacePermissions.REVIEW_WORKSPACE_ENTRY,
        WorkspacePermissions.UPLOAD_WORKSPACE_ATTACHMENTS,
        WorkspacePermissions.FLAG_WORKSPACE_ENTRY,
        WorkspacePermissions.ADD_WORKSPACE_CURRENCY,
    ],
    "OPERATIONS_REVIEWER": [
        OrganizationPermissions.MANAGE_ORGANIZATION,
        WorkspacePermissions.ASSIGN_TEAMS,
        WorkspacePermissions.EXPORT_WORKSPACE_REPORT,
    ],
    "TEAM_COORDINATOR": [
        OrganizationPermissions.MANAGE_ORGANIZATION,
        TeamPermissions.CHANGE_TEAM,
        TeamPermissions.DELETE_TEAM,
        TeamPermissions.VIEW_TEAM,
        TeamPermissions.ADD_TEAM_MEMBER,
    ],
}


def get_permissions_for_role(role_name: str) -> list[str]:
    """
    Returns a list of permission strings for a given role.
    """
    return ROLES.get(role_name.upper(), [])
