from django.db import models


class WorkspacePermissions(models.TextChoices):
    """
    Permissions for the Workspace model.
    """

    CHANGE_WORKSPACE = "change_workspace"  # implemented
    DELETE_WORKSPACE = "delete_workspace"  # implemented
    VIEW_WORKSPACE = "view_workspace"  # implemented
    ASSIGN_TEAMS = "assign_teams"  # implemented
    LOCK_WORKSPACE = "lock_workspace"  
    VIEW_DASHBOARD = "view_dashboard"
    EXPORT_WORKSPACE_REPORT = "export_workspace_report"
    ADD_WORKSPACE_ENTRY = "add_workspace_entry"  # workspace level entry
    CHANGE_WORKSPACE_ENTRY = "change_workspace_entry"
    DELETE_WORKSPACE_ENTRY = "delete_workspace_entry"
    VIEW_WORKSPACE_ENTRY = "view_workspace_entry"
    REVIEW_WORKSPACE_ENTRY = "review_workspace_entry"
    UPLOAD_WORKSPACE_ATTACHMENTS = "upload_workspace_attachments"
    FLAG_WORKSPACE_ENTRY = "flag_workspace_entry"
    CHANGE_TEAM_ENTRY = "change_team_entry"  # team level entry
    DELETE_TEAM_ENTRY = "delete_team_entry"
    VIEW_TEAM_ENTRY = "view_team_entry"
    REVIEW_TEAM_ENTRY = "review_team_entry"
    FLAG_TEAM_ENTRY = "flag_team_entry"


class OrganizationPermissions(models.TextChoices):
    """
    Permissions for the Organization model.
    """

    CHANGE_ORGANIZATION = "change_organization"  # implemented
    DELETE_ORGANIZATION = "delete_organization"
    VIEW_ORGANIZATION = "view_organization"

    ADD_WORKSPACE = "add_workspace"  # can add workspace to organization # implemented

    INVITE_ORG_MEMBER = "invite_org_member"  # can invite org member to organization # implemented
    ADD_ORG_ENTRY = "add_org_entry"  # can add org entry to organization # implemented
    VIEW_ORG_ENTRY = "view_org_entry"  # can view org entry to organization # implemented