from apps.organizations.permissions import OrganizationPermissions
from apps.workspaces.permissions import WorkspacePermissions
from apps.entries.permissions import EntryPermissions
from apps.remittance.permissions import RemittancePermissions


ROLES = {
    "ORG_OWNER": [
        OrganizationPermissions.CHANGE_ORGANIZATION,
        OrganizationPermissions.DELETE_ORGANIZATION,
        OrganizationPermissions.VIEW_ORGANIZATION,
        WorkspacePermissions.ADD_WORKSPACE,
        WorkspacePermissions.ASSIGN_TEAMS,
        WorkspacePermissions.CHANGE_WORKSPACE,
        WorkspacePermissions.DELETE_WORKSPACE,
        WorkspacePermissions.VIEW_WORKSPACE,
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.ADD_ENTRY,
        EntryPermissions.UPLOAD_ATTACHMENTS,
        EntryPermissions.CHANGE_ENTRY,
        EntryPermissions.REVIEW_ENTRY,
        EntryPermissions.FLAG_ENTRY,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.EXPORT_REPORT,
        WorkspacePermissions.LOCK_WORKSPACE,
        RemittancePermissions.VIEW_REMITTANCE,
        RemittancePermissions.ADD_REMITTANCE,
        RemittancePermissions.CHANGE_REMITTANCE,
        RemittancePermissions.DELETE_REMITTANCE,
        RemittancePermissions.REVIEW_REMITTANCE,
        RemittancePermissions.FLAG_REMITTANCE,
    ],
    "WORKSPACE_ADMIN": [
        WorkspacePermissions.CHANGE_WORKSPACE,
        WorkspacePermissions.DELETE_WORKSPACE,
        WorkspacePermissions.VIEW_WORKSPACE,
        WorkspacePermissions.ASSIGN_TEAMS,
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.CHANGE_ENTRY,
        EntryPermissions.REVIEW_ENTRY,
        EntryPermissions.FLAG_ENTRY,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.EXPORT_REPORT,
        WorkspacePermissions.LOCK_WORKSPACE,
        RemittancePermissions.VIEW_REMITTANCE,
        RemittancePermissions.ADD_REMITTANCE,
        RemittancePermissions.CHANGE_REMITTANCE,
        RemittancePermissions.DELETE_REMITTANCE,
        RemittancePermissions.REVIEW_REMITTANCE,
        RemittancePermissions.FLAG_REMITTANCE,
    ],
    "OPERATION_REVIEWER": [
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.CHANGE_ENTRY,
        EntryPermissions.REVIEW_ENTRY,
        EntryPermissions.FLAG_ENTRY,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.EXPORT_REPORT,
        RemittancePermissions.VIEW_REMITTANCE,
        RemittancePermissions.ADD_REMITTANCE,
        RemittancePermissions.CHANGE_REMITTANCE,
        RemittancePermissions.DELETE_REMITTANCE,
        RemittancePermissions.REVIEW_REMITTANCE,
        RemittancePermissions.FLAG_REMITTANCE,
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
        WorkspacePermissions.EXPORT_REPORT,
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
