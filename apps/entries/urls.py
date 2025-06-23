from django.urls import path
from .views import OrganizationExpenseListView, OrganizationExpenseCreateView, OrganizationExpenseUpdateView

urlpatterns = [
    path(
        "expenses/",
        OrganizationExpenseListView.as_view(),
        name="organization_expenses",
    ),
    path(
        "expenses/create/",
        OrganizationExpenseCreateView.as_view(),
        name="organization_expenses_create",
    ),
    path(
        "expenses/<uuid:organization_expense_entry_id>/",
        OrganizationExpenseUpdateView.as_view(),
        name="organization_expense_update"
    )
]
