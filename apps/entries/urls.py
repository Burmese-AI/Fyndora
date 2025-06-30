from django.urls import path
from .views.views import (
    OrganizationExpenseListView,
    OrganizationExpenseCreateView,
    OrganizationExpenseUpdateView,
    WorkspaceExpenseListView,
    WorkspaceExpenseCreateView,
)
from .views.base import EntryDetailView

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
        "expenses/<uuid:pk>/",
        OrganizationExpenseUpdateView.as_view(),
        name="organization_expense_update",
    ),
    path(
        "entries/<uuid:pk>/detail",
        EntryDetailView.as_view(),
        name="entry_detail",
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
]
