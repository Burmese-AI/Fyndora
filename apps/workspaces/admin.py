from django.contrib import admin
from apps.workspaces.models import Workspace, WorkspaceTeam


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = (
        "workspace_id",
        "title",
        "organization",
        "status",
        "created_at",
    )
    list_filter = ("status", "organization")
    search_fields = ("title", "organization__title")
    readonly_fields = ("workspace_id", "created_at", "updated_at")


@admin.register(WorkspaceTeam)
class WorkspaceTeamAdmin(admin.ModelAdmin):
    list_display = ("workspace_team_id", "workspace", "team", "created_at")
    search_fields = ("workspace__title", "team__title")
    readonly_fields = ("workspace_team_id", "created_at", "updated_at")
