from django.urls import path
from apps.workspaces.views import (
    get_workspaces,
    create_workspace,
    edit_workspace,
    delete_workspace,
    add_team_to_workspace,
    get_workspace_teams,
    remove_team_from_workspace,
)

urlpatterns = [
    path("", get_workspaces, name="workspace_list"),
    path("create/", create_workspace, name="create_workspace"),
    path("edit/<uuid:workspace_id>/", edit_workspace, name="edit_workspace"),
    path("delete/<uuid:workspace_id>/", delete_workspace, name="delete_workspace"),
    path(
        "add-team/<uuid:workspace_id>/",
        add_team_to_workspace,
        name="add_team_to_workspace",
    ),
    path(
        "<uuid:workspace_id>/teams/",
        get_workspace_teams,
        name="get_workspace_teams",
    ),
    path(
        "<uuid:workspace_id>/teams/<uuid:team_id>/remove/",
        remove_team_from_workspace,
        name="remove_team_from_workspace",
    ),
]
