from apps.core.permissions import OrganizationPermissions
from apps.core.permissions import WorkspacePermissions
from apps.entries.permissions import EntryPermissions
from apps.remittance.permissions import RemittancePermissions


ROLES = {
    "ORG_OWNER": [
        OrganizationPermissions.CHANGE_ORGANIZATION,
        OrganizationPermissions.DELETE_ORGANIZATION,
        OrganizationPermissions.VIEW_ORGANIZATION,
        OrganizationPermissions.ADD_WORKSPACE,
    ],
    "WORKSPACE_ADMIN": [
        OrganizationPermissions.ADD_WORKSPACE,
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
        WorkspacePermissions.CHANGE_TEAM_ENTRY,
        WorkspacePermissions.DELETE_TEAM_ENTRY,
        WorkspacePermissions.VIEW_TEAM_ENTRY,
        WorkspacePermissions.REVIEW_TEAM_ENTRY,
        WorkspacePermissions.FLAG_TEAM_ENTRY,
    ],
    "OPERATIONS_REVIEWER": [
        WorkspacePermissions.ASSIGN_TEAMS,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.EXPORT_WORKSPACE_REPORT,
        WorkspacePermissions.ADD_WORKSPACE_ENTRY,
        WorkspacePermissions.CHANGE_WORKSPACE_ENTRY,
        WorkspacePermissions.DELETE_WORKSPACE_ENTRY,
        WorkspacePermissions.VIEW_WORKSPACE_ENTRY,
        WorkspacePermissions.REVIEW_WORKSPACE_ENTRY,
        WorkspacePermissions.UPLOAD_WORKSPACE_ATTACHMENTS,
        WorkspacePermissions.FLAG_WORKSPACE_ENTRY,
        WorkspacePermissions.CHANGE_TEAM_ENTRY,
        WorkspacePermissions.DELETE_TEAM_ENTRY,
        WorkspacePermissions.VIEW_TEAM_ENTRY,
        WorkspacePermissions.REVIEW_TEAM_ENTRY,
        WorkspacePermissions.FLAG_TEAM_ENTRY,
    ],
    "TEAM_COORDINATOR": [
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.ADD_ENTRY,
        EntryPermissions.UPLOAD_ATTACHMENTS,
        EntryPermissions.CHANGE_ENTRY,
        EntryPermissions.REVIEW_ENTRY,
        EntryPermissions.FLAG_ENTRY,
        WorkspacePermissions.VIEW_DASHBOARD,
        RemittancePermissions.VIEW_REMITTANCE,
        RemittancePermissions.FLAG_REMITTANCE,
    ],
    "RECORD_SUBMITTER": [
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.ADD_ENTRY,
        EntryPermissions.UPLOAD_ATTACHMENTS,
        EntryPermissions.CHANGE_ENTRY,
    ],
    "QUALITY_AUDITOR": [
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.REVIEW_ENTRY,
        EntryPermissions.FLAG_ENTRY,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.EXPORT_WORKSPACE_REPORT,
        RemittancePermissions.VIEW_REMITTANCE,
        RemittancePermissions.FLAG_REMITTANCE,
    ],
    "SYSTEM_ASSISTANT": [
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.REVIEW_ENTRY,
        EntryPermissions.FLAG_ENTRY,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.LOCK_WORKSPACE,
    ],
}


def get_permissions_for_role(role_name: str) -> list[str]:
    """
    Returns a list of permission strings for a given role.
    """
    return ROLES.get(role_name.upper(), [])
