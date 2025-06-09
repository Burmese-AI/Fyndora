from django.urls import path
from apps.workspaces.views import WorkspaceListView

urlpatterns = [
    path("", WorkspaceListView.as_view(), name="workspace_list"),
]