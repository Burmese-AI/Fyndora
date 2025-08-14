from typing import Any
import csv
from datetime import datetime
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
)
from decimal import Decimal
from apps.workspaces.mixins.workspaces.mixins import WorkspaceFilteringMixin
from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.organizations.models import Organization
from apps.entries.constants import EntryType, EntryStatus
from apps.core.services.file_export_services import (
    CsvExporter,
    # PdfExporter
)
from pprint import pprint
from apps.entries.selectors import get_total_amount_of_entries
from .services import export_overview_finance_report

class OverviewFinanceReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    WorkspaceFilteringMixin,
    TemplateView,
):
    template_name = "reports/overview_finance_report_index.html"
    content_template_name = "reports/partials/overview_balance_sheet.html"
    
    def _get_workspace_team_context(self, workspace_team: WorkspaceTeam):
        team_income = get_total_amount_of_entries(
            entry_type=EntryType.INCOME, 
            entry_status=EntryStatus.APPROVED, 
            workspace_team=workspace_team
        )
        
        team_expense = get_total_amount_of_entries(
            entry_type=EntryType.DISBURSEMENT, 
            entry_status=EntryStatus.APPROVED, 
            workspace_team=workspace_team
        )

        net_income = team_income - team_expense
        due_amount = workspace_team.remittance.due_amount or Decimal("0.00")

        return {
            "title": workspace_team.team.title,
            "total_income": team_income,
            "total_expense": team_expense,
            "net_income": net_income,
            "remittance_rate": workspace_team.custom_remittance_rate,
            "org_share": due_amount,
        }
      
    def _get_workspace_context(self, workspace: Workspace):
        children_qs = workspace.workspace_teams.select_related("team").all()
        context_children = []
        # Totals for workspace
        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")
        total_org_share = Decimal("0.00")

        for ws_team in children_qs:
            ws_team_context = self._get_workspace_team_context(ws_team)
            context_children.append(ws_team_context)
            total_income += ws_team_context["total_income"]
            total_expense += ws_team_context["total_expense"]
            total_org_share += ws_team_context["org_share"]

        workspace_expenses = get_total_amount_of_entries(
            entry_type=EntryType.WORKSPACE_EXP,
            entry_status=EntryStatus.APPROVED,
            workspace=workspace
        )

        return {
            "title": workspace.title,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_income": total_income - total_expense,
            "org_share": total_org_share,
            "parent_lvl_total_expense": workspace_expenses,
            "final_net_profit": total_org_share - workspace_expenses,
            "context_children": context_children
        }
      
    def _get_organization_context(self, org: Organization):
        children_qs = self.organization.workspaces.all()
        context_children = []
        # Totals for workspace
        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")
        total_org_share = Decimal("0.00")
        for ws in children_qs:
            ws_context = self._get_workspace_context(ws)
            context_children.append(ws_context)
            total_income += ws_context["total_income"]
            total_expense += ws_context["total_expense"]
            total_org_share += ws_context["final_net_profit"]
            #Turn this parent context format into child context format
            ws_context = {
                "title": ws_context["title"],
                "total_income": ws_context["total_income"],
                "total_expense": ws_context["total_expense"],
                "net_income": ws_context["net_income"],
                "parent_lvl_total_expense": ws_context["parent_lvl_total_expense"],
                "org_share": ws_context["final_net_profit"],
            }
        org_expenses = get_total_amount_of_entries(
            entry_type=EntryType.ORG_EXP,
            entry_status=EntryStatus.APPROVED,
            org=org
        )
        return {
            "title": org.title,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_income": total_income - total_expense,
            "org_share": total_org_share,
            "parent_lvl_total_expense": org_expenses,
            "final_net_profit": total_org_share - org_expenses,
            "context_children": context_children
        }
      
    def get_context_data(self, **kwargs) -> dict[str, any]:
        workspace_filter = self.request.GET.get("workspace") or None

        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "overview"
        base_context["workspace_filter"] = workspace_filter

        context_parent = None
        context_children = []

        # workspace_filter exists, Workspace Lvl Report
        try:
            if workspace_filter:
                workspace = Workspace.objects.get(pk=workspace_filter, organization=self.organization)
                if not workspace:
                    raise ValueError("Invalid workspace selected.")
                context_parent = self._get_workspace_context(workspace)
                context_children = context_parent.pop("context_children")
                context_parent["parent_expense_label"] = "Workspace Expenses"

            else:
                context_parent = self._get_organization_context(self.organization)
                context_children = context_parent.pop("context_children")
                context_parent["parent_expense_label"] = "Org Expenses"
        except Exception as e:
            print(f"An error occurred: {e}")

        base_context["context_parent"] = context_parent
        base_context["context_children"] = context_children
        print("=" * 100)
        pprint(base_context)
        print("=" * 100)
        return base_context

    def post(self, request, *args, **kwargs):
        export_format = request.GET.get("format", "csv").lower()
        context = self.get_context_data(**kwargs)

        if export_format == "csv":
            return export_overview_finance_report(context, CsvExporter)
        elif export_format == "pdf":
            return export_overview_finance_report(context, CsvExporter)
        else:
            raise Http404(f"Unsupported export format: {export_format}")
    
    def _export_to_csv(self, context):
        """Generate CSV export matching the HTML table layout"""
        workspace_filter = self.request.GET.get("workspace") or None
        filename = (
            f"finance-report-workspace-{context['context_parent']['title']}-{datetime.now().date()}.csv"
            if workspace_filter
            else f"finance-report-organization-{datetime.now().date()}.csv"
        )

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Header row (matches table <thead>)
        header_first_col = "Team" if workspace_filter else "Workspace"
        writer.writerow([header_first_col, "Total Income", "Total Expense", "Net Income", "Org Share"])

        # Children rows
        for child in context['context_children']:
            # This matches exactly what’s rendered in <tbody>
            writer.writerow([
                child['title'],
                f"{child['total_income']:.2f}",
                f"{child['total_expense']:.2f}",
                f"{child['net_income']:.2f}" if 'net_income' in child else "",
                f"{child['org_share']:.2f}" if 'org_share' in child else "",
            ])

        # Blank row before totals
        writer.writerow([])

        # Totals row (matches first <tfoot> row)
        parent = context['context_parent']
        writer.writerow([
            "Total",
            f"{parent['total_income']:.2f}",
            f"{parent['total_expense']:.2f}",
            f"{parent['net_income']:.2f}",
            f"{parent['org_share']:.2f}",
        ])

        # Parent expenses & final net profit (matches second <tfoot> row)
        writer.writerow([
            parent['parent_expense_label'],
            f"{parent['parent_lvl_total_expense']:.2f}",
            "",
            "Final Net Profit",
            f"{parent['final_net_profit']:.2f}",
        ])

        return response

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
