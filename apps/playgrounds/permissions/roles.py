from apps.organizations.permissions import OrganizationPermissions
from apps.core.permissions import WorkspacePermissions
from apps.entries.permissions import EntryPermissions
from apps.remittance.permissions import RemittancePermissions
from enum import Enum

class Role(str, Enum):
    ORG_OWNER = "ORG_OWNER"
    WORKSPACE_ADMIN = "WORKSPACE_ADMIN"
    OPERATIONS_REVIEWER = "OPERATIONS_REVIEWER"
    TEAM_COORDINATOR = "TEAM_COORDINATOR"
    RECORD_SUBMITTER = "RECORD_SUBMITTER"
    QUALITY_AUDITOR = "QUALITY_AUDITOR"
    SYSTEM_ASSISTANT = "SYSTEM_ASSISTANT"
    
    @property
    def label(self):
        return self.name.replace("_", " ").title()

    @classmethod
    def choices(cls):
        return [(role.value, role.name.replace("_", " ").title()) for role in cls]

ROLE_PERMISSIONS = {
    Role.ORG_OWNER.value: [
        OrganizationPermissions.CHANGE_ORGANIZATION,
        OrganizationPermissions.DELETE_ORGANIZATION,
        OrganizationPermissions.VIEW_ORGANIZATION,
        OrganizationPermissions.ADD_WORKSPACE,
    ],
    Role.WORKSPACE_ADMIN.value: [
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
    Role.OPERATIONS_REVIEWER.value: [
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
    Role.TEAM_COORDINATOR.value: [
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
    Role.RECORD_SUBMITTER.value: [
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.ADD_ENTRY,
        EntryPermissions.UPLOAD_ATTACHMENTS,
        EntryPermissions.CHANGE_ENTRY,
    ],
    Role.QUALITY_AUDITOR.value: [
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.REVIEW_ENTRY,
        EntryPermissions.FLAG_ENTRY,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.EXPORT_WORKSPACE_REPORT,
        RemittancePermissions.VIEW_REMITTANCE,
        RemittancePermissions.FLAG_REMITTANCE,
    ],
    Role.SYSTEM_ASSISTANT.value: [
        EntryPermissions.VIEW_ENTRY,
        EntryPermissions.REVIEW_ENTRY,
        EntryPermissions.FLAG_ENTRY,
        WorkspacePermissions.VIEW_DASHBOARD,
        WorkspacePermissions.LOCK_WORKSPACE,
    ],
}
