from django.shortcuts import render
from typing import Any
from django.views.generic import TemplateView
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
)
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from decimal import Decimal
from apps.workspaces.mixins.workspaces.mixins import WorkspaceFilteringMixin
from apps.entries.models import Entry
from apps.workspaces.models import Workspace
from apps.organizations.models import Organization
from apps.remittance.models import Remittance
from apps.entries.constants import EntryType, EntryStatus
from pprint import pprint

class OverviewFinanceReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    WorkspaceFilteringMixin,
    TemplateView
):
    
    template_name = "reports/overview_finance_report_index.html"
    content_template_name = "reports/partials/overview_balance_sheet.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        workspace_filter = self.request.GET.get("workspace") or None
        
        base_context = super().get_context_data(**kwargs)
        base_context["view"] = "overview"
        base_context["workspace_filter"] = workspace_filter

        if workspace_filter:
            workspace_obj = Workspace.objects.get(pk=workspace_filter)

            workspace_teams_qs = workspace_obj.workspace_teams.select_related("team").all()

            workspace_teams_list = []

            # Totals for the whole workspace
            ws_total_income = Decimal("0.00")
            ws_total_disbursement = Decimal("0.00")
            ws_total_org_share = Decimal("0.00")

            for ws_team in workspace_teams_qs:
                team_pk = ws_team.team.pk

                # Total approved income for team
                total_income = ws_team.entries.filter(
                    entry_type=EntryType.INCOME,
                    status=EntryStatus.APPROVED
                ).aggregate(
                    total=Sum(
                        ExpressionWrapper(
                            F("amount") * F("exchange_rate_used"),
                            output_field=DecimalField(max_digits=20, decimal_places=2)
                        )
                    )
                )["total"] or Decimal("0.00")

                # Total approved disbursements for team
                total_disbursement = ws_team.entries.filter(
                    entry_type=EntryType.DISBURSEMENT,
                    status=EntryStatus.APPROVED
                ).aggregate(
                    total=Sum(
                        ExpressionWrapper(
                            F("amount") * F("exchange_rate_used"),
                            output_field=DecimalField(max_digits=20, decimal_places=2)
                        )
                    )
                )["total"] or Decimal("0.00")

                net_income = total_income - total_disbursement

                # Get org share from linked remittance
                paid_amount = ws_team.remittance.due_amount or Decimal("0.00")

                workspace_teams_list.append({
                    "pk": team_pk,
                    "total_income": total_income,
                    "total_disbursement": total_disbursement,
                    "net_income": net_income,
                    "remittance_rate": ws_team.custom_remittance_rate,
                    "org_share": paid_amount
                })

                # Add to workspace totals
                ws_total_income += total_income
                ws_total_disbursement += total_disbursement
                ws_total_org_share += paid_amount

            # Workspace-level expense
            workspace_expenses = workspace_obj.entries.filter(
                entry_type=EntryType.WORKSPACE_EXP, 
                status=EntryStatus.APPROVED
            ).aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F("amount") * F("exchange_rate_used"),
                        output_field=DecimalField(max_digits=20, decimal_places=2)
                    )
                )
            )["total"] or Decimal("0.00")

            ws_net_income = ws_total_income - ws_total_disbursement
            final_net_profit = ws_net_income - workspace_expenses

            workspace_dict = {
                "title": workspace_obj.title,
                "total_income": ws_total_income,
                "total_disbursement": ws_total_disbursement,
                "net_income": ws_net_income,
                "org_share": ws_total_org_share,
                "workspace_expenses": workspace_expenses,
                "final_net_profit": final_net_profit,
            }

            base_context["workspace_teams"] = workspace_teams_list
            base_context["workspace"] = workspace_dict

        else:
            pass
        
        pprint(base_context)
        return base_context

    def render_to_response(self, context, **response_kwargs):
        if self.request.htmx:
            return render(self.request, self.content_template_name, context)
        return super().render_to_response(context, **response_kwargs)
        
class RemittanceReportView(
    OrganizationRequiredMixin,
    HtmxInvalidResponseMixin,
    WorkspaceFilteringMixin,
    TemplateView
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
    TemplateView
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
