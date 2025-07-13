from django.db import models


class WorkspacePermissions(models.TextChoices):
    """
    Permissions for the Workspace model.
    """

    ADD_WORKSPACE = "add_workspace"
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
    CHANGE_TEAM_ENTRY = "change_team_entry"  # team level entry
    DELETE_TEAM_ENTRY = "delete_team_entry"
    VIEW_TEAM_ENTRY = "workspaces.view_team_entry"
    REVIEW_TEAM_ENTRY = "workspaces.review_team_entry"
    FLAG_TEAM_ENTRY = "workspaces.flag_team_entry"
