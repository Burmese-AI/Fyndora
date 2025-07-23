from django.db import models


class WorkspacePermissions(models.TextChoices):
    """
    Permissions for the Workspace model.
    """

    CHANGE_WORKSPACE = "change_workspace"  
    DELETE_WORKSPACE = "delete_workspace"  
    VIEW_WORKSPACE = "view_workspace"  
    ASSIGN_TEAMS = "assign_teams"  
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


class OrganizationPermissions(models.TextChoices):
    """
    Permissions for the Organization model.
    """

    CHANGE_ORGANIZATION = "change_organization"  # implemented
    DELETE_ORGANIZATION = "delete_organization"
    VIEW_ORGANIZATION = "view_organization"

    CHANGE_WORKSPACE_ADMIN = (
        "edit_workspace_admin"  # can edit workspace admin # implemented
    )

    ADD_WORKSPACE = "add_workspace"  # can add workspace to organization # implemented
    ADD_TEAM = "add_team"  # can add team to organization # implemented

    INVITE_ORG_MEMBER = (
        "invite_org_member"  # can invite org member to organization # implemented
    )
    ADD_ORG_ENTRY = "add_org_entry"  # can add org entry to organization # implemented
    VIEW_ORG_ENTRY = (
        "view_org_entry"  # can view org entry to organization # implemented
    )
    CHANGE_ORG_ENTRY = (
        "change_org_entry"  # can change org entry to organization # implemented
    )
    DELETE_ORG_ENTRY = (
        "delete_org_entry"  # can delete org entry to organization # implemented
    )


class TeamPermissions(models.TextChoices):
    """
    Permissions for the Team model.
    """

    CHANGE_TEAM = "change_team"  # can change team # implemented
    DELETE_TEAM = "delete_team"
    VIEW_TEAM = "view_team"
    ADD_TEAM_MEMBER = "add_team_member"
