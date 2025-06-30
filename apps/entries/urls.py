from django.urls import path
from .views.views import (
    OrganizationExpenseListView,
    OrganizationExpenseCreateView,
    OrganizationExpenseUpdateView,
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
]
