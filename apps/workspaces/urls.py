from django.urls import path
from apps.workspaces.views import (
    WorkspaceListView,
    create_workspace,
    edit_workspace,
    delete_workspace,
)

urlpatterns = [
    path("", WorkspaceListView.as_view(), name="workspace_list"),
    path("create/", create_workspace, name="create_workspace"),
    path("edit/<uuid:workspace_id>/", edit_workspace, name="edit_workspace"),
    path("delete/<uuid:workspace_id>/", delete_workspace, name="delete_workspace"),
]
