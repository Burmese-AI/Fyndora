from django.urls import path
from .views.organizatin_expense import (
    OrganizationExpenseListView,
    OrganizationExpenseCreateView,
    OrganizationExpenseUpdateView,
    OrganizationExpenseDetailView,
)

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
        name="organization_expense_update"
    ),
    path(
        "expenses/<uuid:pk>/view",
        OrganizationExpenseDetailView.as_view(),
        name="organization_expense_detail",
    ),
]
