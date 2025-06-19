from django.urls import path
from apps.workspaces.views import (
    get_workspaces_view,
    create_workspace_view,
    edit_workspace_view,
    delete_workspace_view,
    add_team_to_workspace_view,
    get_workspace_teams_view,
    remove_team_from_workspace_view,
    test1_view,
)

urlpatterns = [
    path("", get_workspaces_view, name="workspace_list"),
    path("create/", create_workspace_view, name="create_workspace"),
    path("edit/<uuid:workspace_id>/", edit_workspace_view, name="edit_workspace"),
    path("delete/<uuid:workspace_id>/", delete_workspace_view, name="delete_workspace"),
    path(
        "add-team/<uuid:workspace_id>/",
        add_team_to_workspace_view,
        name="add_team_to_workspace",
    ),
    path(
        "<uuid:workspace_id>/teams/",
        get_workspace_teams_view,
        name="get_workspace_teams",
    ),
    path(
        "<uuid:workspace_id>/teams/<uuid:team_id>/remove/",
        remove_team_from_workspace_view,
        name="remove_team_from_workspace",
    ),
    path(
        "<uuid:workspace_id>/teams/test1/",
        test1_view,
        name="test1",
    ),
]
