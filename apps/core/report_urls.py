from django.urls import path
from .views.views import OverviewFinanceReportView, RemittanceReportView

urlpatterns = [
    path(
        "report",
        OverviewFinanceReportView.as_view(),
        name="overview_finance_report"
    ),
    path(
        "remittance-report",
        RemittanceReportView.as_view(),
        name="remittance_report"
    ),
]
