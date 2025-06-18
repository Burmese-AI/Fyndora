from django.urls import path
from .views import OrganizationExpenseListView

urlpatterns = [
    path(
        "expenses/", OrganizationExpenseListView.as_view(), name="organization_expenses"
    ),
]
