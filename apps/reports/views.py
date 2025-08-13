from django.shortcuts import render
from typing import Any
from django.views.generic import TemplateView
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
)
from apps.workspaces.mixins.workspaces.mixins import WorkspaceFilteringMixin


class OverviewFinanceReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    WorkspaceFilteringMixin,
    TemplateView,
):
    template_name = "reports/overview_finance_report_index.html"
    content_template_name = "reports/partials/sample_balance_sheet.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "overview"
        return base_context

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return render(self.request, self.content_template_name, context)
        return super().render_to_response(context, **response_kwargs)


class RemittanceReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    WorkspaceFilteringMixin,
    TemplateView,
):
    template_name = "reports/remittance_report_index.html"
    content_template_name = "reports/partials/remittance_balance_sheet.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "remittance"
        return base_context

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return render(self.request, self.content_template_name, context)
        return super().render_to_response(context, **response_kwargs)


class EntryReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    WorkspaceFilteringMixin,
    TemplateView,
):
    template_name = "reports/entry_report_index.html"
    content_template_name = "reports/partials/entry_balance_sheet.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "entry"
        return base_context

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return render(self.request, self.content_template_name, context)
        return super().render_to_response(context, **response_kwargs)
