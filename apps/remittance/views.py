from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import ListView

from apps.core.constants import PAGINATION_SIZE
from apps.teams.models import Team
from apps.workspaces.models import Workspace

from .constants import STATUS_CHOICES
from .models import Remittance
from .selectors import get_remittances_with_filters
from .services import remittance_confirm_payment


class RemittanceListView(LoginRequiredMixin, ListView):
    """
    Main template-based view for listing remittances with filters.
    """

    model = Remittance
    template_name = "remittance/index.html"
    context_object_name = "remittances"
    paginate_by = PAGINATION_SIZE

    def get_template_names(self):
        # If the request is from htmx, return the partial template
        if self.request.META.get("HTTP_HX_REQUEST"):
            return ["remittance/remittance_list.html"]
        # Otherwise, return the full template
        return [self.template_name]

    def get_queryset(self):
        if "workspace_id" not in self.kwargs:
            raise Http404("Workspace ID not found in URL parameters.")

        return get_remittances_with_filters(
            workspace_id=self.kwargs.get("workspace_id"),
            team_id=self.request.GET.get("team"),
            status=self.request.GET.get("status"),
            start_date=self.request.GET.get("start_date"),
            end_date=self.request.GET.get("end_date"),
            search=self.request.GET.get("q"),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace_id = self.kwargs.get("workspace_id")

        # Get current workspace and add it to context
        workspace = Workspace.objects.filter(pk=workspace_id).first()
        context["workspace"] = workspace

        # Get all teams and statuses for filter dropdowns
        if workspace:
            context["all_teams"] = Team.objects.filter(
                workspace_teams__workspace=workspace
            ).order_by("title")
        else:
            context["all_teams"] = Team.objects.none()

        context["all_statuses"] = STATUS_CHOICES

        # Preserve existing filters for pagination and search query
        context["current_filters"] = self.request.GET.copy()
        if "page" in context["current_filters"]:
            context["current_filters"].pop("page")
        context["search_query"] = self.request.GET.get("q", "")
        context["workspace_id"] = self.kwargs.get("workspace_id")
        return context


class RemittanceConfirmPaymentView(LoginRequiredMixin, View):
    """
    View to handle the confirmation of a remittance payment.
    """

    def post(self, request, *args, **kwargs):
        remittance_id = kwargs.get("remittance_id")
        remittance = get_object_or_404(Remittance, pk=remittance_id)

        try:
            updated_remittance = remittance_confirm_payment(
                remittance=remittance, user=request.user
            )

            context = {
                "remittance": updated_remittance,
                "workspace": updated_remittance.workspace,
            }
            return render(request, "remittance/remittance_row.html", context)

        except (PermissionDenied, ValidationError) as e:
            messages.error(request, str(e))
            response = HttpResponse(status=204)
            response["HX-Refresh"] = "true"
            return response
