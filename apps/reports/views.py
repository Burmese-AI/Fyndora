from decimal import Decimal
from typing import Any

from django.shortcuts import render
from django.views.generic import TemplateView

from apps.core.views.mixins import (
    HtmxInvalidResponseMixin,
    OrganizationRequiredMixin,
)
from apps.workspaces.mixins.workspaces.mixins import WorkspaceFilteringMixin
from apps.workspaces.models import Workspace, WorkspaceTeam

from apps.reports.permissions import can_view_report_page
from apps.core.utils import permission_denied_view


from apps.organizations.models import Organization
from apps.entries.constants import EntryType, EntryStatus
from apps.entries.selectors import get_total_amount_of_entries
from apps.core.services.file_export_services import CsvExporter, PdfExporter
from .services import export_overview_finance_report
from apps.reports.selectors import EntrySelectors, RemittanceSelectors


class OverviewFinanceReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    WorkspaceFilteringMixin,
    TemplateView,
):
    template_name = "reports/overview_finance_report_index.html"
    content_template_name = "reports/partials/overview_balance_sheet.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_view_report_page(request.user, self.organization):
            return permission_denied_view(
                request,
                "You do not have permission to view the report page.",
            )
        return super().dispatch(request, *args, **kwargs)

    def _get_team_context(self, workspace_team: WorkspaceTeam):
        income = get_total_amount_of_entries(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )
        expense = get_total_amount_of_entries(
            entry_type=EntryType.DISBURSEMENT,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )
        net_income = income - expense
        due_amount = workspace_team.remittance.due_amount or Decimal("0.00")

        return {
            "title": workspace_team.team.title,
            "total_income": round(income, 2),
            "total_expense": round(expense, 2),
            "net_income": round(net_income, 2),
            "remittance_rate": workspace_team.custom_remittance_rate,
            "org_share": round(due_amount, 2),  # contribution to org
        }

    def _get_workspace_context(self, workspace: Workspace):
        teams = workspace.joined_teams.select_related("team").all()
        team_contexts = []
        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")
        total_org_share = Decimal("0.00")

        for team in teams:
            team_ctx = self._get_team_context(team)
            team_contexts.append(team_ctx)
            total_income += team_ctx["total_income"]
            total_expense += team_ctx["total_expense"]
            total_org_share += team_ctx["org_share"]

        workspace_expenses = get_total_amount_of_entries(
            entry_type=EntryType.WORKSPACE_EXP,
            entry_status=EntryStatus.APPROVED,
            workspace=workspace,
        )

        final_net_profit = total_org_share - workspace_expenses

        return {
            "title": workspace.title,
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "net_income": round(total_income - total_expense, 2),
            "org_share": round(total_org_share, 2),  # before workspace expenses
            "parent_lvl_total_expense": round(workspace_expenses, 2),
            "final_net_profit": round(final_net_profit, 2),
            "children": team_contexts,  # nested teams
        }

    def _get_organization_context(self, org: Organization):
        workspaces = org.workspaces.all()
        workspace_contexts = []
        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")
        total_org_share = Decimal("0.00")

        for ws in workspaces:
            ws_ctx = self._get_workspace_context(ws)
            workspace_contexts.append(ws_ctx)
            total_income += ws_ctx["total_income"]
            total_expense += ws_ctx["total_expense"]
            total_org_share += ws_ctx["final_net_profit"]  # after workspace expenses

        org_expenses = get_total_amount_of_entries(
            entry_type=EntryType.ORG_EXP,
            entry_status=EntryStatus.APPROVED,
            org=org,
        )
        final_net_profit = total_org_share - org_expenses

        return {
            "title": org.title,
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "net_income": round(total_income - total_expense, 2),
            "org_share": round(total_org_share, 2),  # sum of workspace profits
            "parent_lvl_total_expense": round(org_expenses, 2),
            "final_net_profit": round(final_net_profit, 2),
            "children": workspace_contexts,
        }

    def get_context_data(self, **kwargs) -> dict[str, any]:
        workspace_filter = self.request.GET.get("workspace") or None
        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "overview"
        base_context["workspace_filter"] = workspace_filter

        try:
            if workspace_filter:
                workspace = Workspace.objects.get(
                    pk=workspace_filter, organization=self.organization
                )
                # workspace context uses workspace_* keys
                org_data = self._get_workspace_context(workspace)
                org_data["level"] = "workspace"
            else:
                # org context uses org_* keys
                org_data = self._get_organization_context(self.organization)
                org_data["level"] = "org"
        except Exception as e:
            print(f"Error fetching report data: {e}")
            org_data = None

        base_context["report_data"] = org_data
        # pprint(base_context["report_data"])
        return base_context

    def post(self, request, *args, **kwargs):
        export_format = (
            request.POST.get("format") or request.GET.get("format", "csv")
        ).lower()
        context = self.get_context_data(**kwargs)
        if export_format == "csv":
            return export_overview_finance_report(context, CsvExporter)
        elif export_format == "pdf":
            return export_overview_finance_report(context, PdfExporter)
        else:
            raise Http404(f"Unsupported export format: {export_format}")

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
        workspace_filter = self.request.GET.get("workspace") or None

        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "remittance"
        base_context["workspace_filter"] = workspace_filter

        # Get remittance statistics
        remittance_stats = RemittanceSelectors.get_summary_stats(
            organization_id=self.organization.pk, workspace_id=workspace_filter
        )

        # Calculate payment progress percentage
        total_due = remittance_stats["total_due"]
        total_paid = remittance_stats["total_paid"]
        payment_progress = 0
        if total_due > 0:
            payment_progress = round((total_paid / total_due) * 100, 1)

        base_context.update(
            {
                "total_due": total_due,
                "total_paid": total_paid,
                "overdue_amount": remittance_stats["overdue_amount"],
                "remaining_due": remittance_stats["remaining_due"],
                "payment_progress": payment_progress,
            }
        )

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
        workspace_filter = self.request.GET.get("workspace") or None

        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "entry"
        base_context["workspace_filter"] = workspace_filter

        # Get entry statistics
        entry_stats = EntrySelectors.get_summary_stats(
            organization_id=self.organization.pk, workspace_id=workspace_filter
        )

        base_context.update(
            {
                "total_entries": entry_stats["total_entries"],
                "pending_entries": entry_stats["pending_entries"],
                "approved_entries": entry_stats["approved_entries"],
                "rejected_entries": entry_stats["rejected_entries"],
            }
        )

        return base_context

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return render(self.request, self.content_template_name, context)
        return super().render_to_response(context, **response_kwargs)


# organization_report = {
#     "title": org.title,
#     "total_income": Decimal(...),
#     "total_expense": Decimal(...),
#     "net_income": Decimal(...),
#     "org_share": Decimal(...),
#     "parent_lvl_total_expense": Decimal(...),  # org-level expense
#     "final_net_profit": Decimal(...),
#     "children": [  # workspaces
#         {
#             "title": workspace.title,
#             "total_income": Decimal(...),
#             "total_expense": Decimal(...),
#             "net_income": Decimal(...),
#             "org_share": Decimal(...),  # sum of team org shares - workspace expenses
#             "parent_lvl_total_expense": Decimal(...),  # workspace-level expenses
#             "final_net_profit": Decimal(...),
#             "children": [  # teams
#                 {
#                     "title": team.title,
#                     "total_income": Decimal(...),
#                     "total_expense": Decimal(...),
#                     "net_income": Decimal(...),
#                     "remittance_rate": team.custom_remittance_rate,
#                     "org_share": Decimal(...),  # remittance due amount
#                 },
#                 # more teams
#             ],
#         },
#         # more workspaces
#     ],
# }
