from django.db import models
class WorkspacePermissions(models.TextChoices):
    """
    Permissions for the Workspace model.
    """

    ADD_WORKSPACE = "workspaces.add_workspace"
    CHANGE_WORKSPACE = "workspaces.change_workspace"
    DELETE_WORKSPACE = "workspaces.delete_workspace"
    VIEW_WORKSPACE = "workspaces.view_workspace"
    ASSIGN_TEAMS = "workspaces.assign_teams"
    LOCK_WORKSPACE = "workspaces.lock_workspace"
    VIEW_DASHBOARD = "workspaces.view_dashboard"
    EXPORT_WORKSPACE_REPORT = "workspaces.export_workspace_report"
    ADD_WORKSPACE_ENTRY = "workspaces.add_workspace_entry" #workspace level entry
    CHANGE_WORKSPACE_ENTRY = "workspaces.change_workspace_entry"
    DELETE_WORKSPACE_ENTRY = "workspaces.delete_workspace_entry"
    VIEW_WORKSPACE_ENTRY = "workspaces.view_workspace_entry"
    REVIEW_WORKSPACE_ENTRY = "workspaces.review_workspace_entry"
    UPLOAD_WORKSPACE_ATTACHMENTS = "workspaces.upload_workspace_attachments"
    FLAG_WORKSPACE_ENTRY = "workspaces.flag_workspace_entry"
    CHANGE_TEAM_ENTRY = "workspaces.change_team_entry" #team level entry
    DELETE_TEAM_ENTRY = "workspaces.delete_team_entry"
    VIEW_TEAM_ENTRY = "workspaces.view_team_entry"
    REVIEW_TEAM_ENTRY = "workspaces.review_team_entry"
    FLAG_TEAM_ENTRY = "workspaces.flag_team_entry"
