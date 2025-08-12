from django.urls import path
from .views import (
    OverviewFinanceReportView, 
    RemittanceReportView,
    EntryReportView
)

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
    path(
        "entry-report",
        EntryReportView.as_view(),
        name="entry_report"
    ),
]
