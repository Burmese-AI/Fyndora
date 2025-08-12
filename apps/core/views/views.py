from django.shortcuts import render
from typing import Any
from django.views.generic import TemplateView
from .mixins import (
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
)


def close_modal(request):
    return render(request, "components/modal_placeholder.html")


def permission_denied_view(request):
    return render(request, "components/permission_error_page.html")


class OverviewFinanceReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    TemplateView
):
    
    template_name = "entries/overview_report_index.html"
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "overview"
        return base_context