from django.urls import path
from .views.org_expense_views import (
    OrganizationExpenseListView,
    OrganizationExpenseCreateView,
    OrganizationExpenseUpdateView,
    OrganizationExpenseDeleteView,
)
from .views.workspace_expense_views import (
    WorkspaceExpenseListView,
    WorkspaceExpenseCreateView,
    WorkspaceExpenseUpdateView,
    WorkspaceExpenseDeleteView,
)
from .views.entry_views import (
    WorkspaceTeamEntryListView,
    WorkspaceTeamEntryCreateView,
    WorkspaceTeamEntryUpdateView,
    WorkspaceTeamEntryDeleteView,
)
from .views.base_views import EntryDetailView

urlpatterns = [
    path(
        "expenses/",
        OrganizationExpenseListView.as_view(),
        name="organization_expenses",
    ),
    path(
        "expenses/create/",
        OrganizationExpenseCreateView.as_view(),
        name="organization_expense_create",
    ),
    path(
        "expenses/<uuid:pk>/",
        OrganizationExpenseUpdateView.as_view(),
        name="organization_expense_update",
    ),
    path(
        "expenses/<uuid:pk>/delete",
        OrganizationExpenseDeleteView.as_view(),
        name="organization_expense_delete",
    ),
    path(
        "workspaces/<uuid:workspace_id>/expenses",
        WorkspaceExpenseListView.as_view(),
        name="workspace_expense_list",
    ),
    path(
        "workspaces/<uuid:workspace_id>/expenses/create",
        WorkspaceExpenseCreateView.as_view(),
        name="workspace_expense_create",
    ),
    path(
        "workspaces/<uuid:workspace_id>/expenses/<uuid:pk>/",
        WorkspaceExpenseUpdateView.as_view(),
        name="workspace_expense_update",
    ),
    path(
        "workspaces/<uuid:workspace_id>/expenses/<uuid:pk>/delete",
        WorkspaceExpenseDeleteView.as_view(),
        name="workspace_expense_delete",
    ),
    path(
        "workspaces/<uuid:workspace_id>/workspace-teams/<uuid:workspace_team_id>/entries",
        WorkspaceTeamEntryListView.as_view(),
        name="workspace_team_entry_list",
    ),
    path(
        "workspaces/<uuid:workspace_id>/workspace-teams/<uuid:workspace_team_id>/entries/create",
        WorkspaceTeamEntryCreateView.as_view(),
        name="workspace_team_entry_create",
    ),
    path(
        "workspaces/<uuid:workspace_id>/workspace-teams/<uuid:workspace_team_id>/entries/<uuid:pk>",
        WorkspaceTeamEntryUpdateView.as_view(),
        name="workspace_team_entry_update",
    ),
    path(
        "workspaces/<uuid:workspace_id>/workspace-teams/<uuid:workspace_team_id>/entries/<uuid:pk>/delete",
        WorkspaceTeamEntryDeleteView.as_view(),
        name="workspace_team_entry_delete",
    ),
]

urlpatterns += [
    path(
        "entries/<uuid:pk>/detail",
        EntryDetailView.as_view(),
        name="entry_detail",
    ),
]
