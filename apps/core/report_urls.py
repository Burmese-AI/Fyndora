from django.urls import path
from .views.views import OverviewFinanceReportView

urlpatterns = [
    path(
        "report",
        OverviewFinanceReportView.as_view(),
        name="overview_finance_report"
    )
]
