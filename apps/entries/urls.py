from django.urls import path
from .views import OrganizationExpenseListView, OrganizationExpenseCreateView

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
]
