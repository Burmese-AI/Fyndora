from django.http import Http404
from django.views.generic import ListView

from apps.core.constants import PAGINATION_SIZE

from .models import Remittance
from .selectors import get_remittances_with_filters
from .constants import STATUS_CHOICES
from apps.workspaces.models import Workspace
from apps.teams.models import Team


class RemittanceListView(ListView):
    """
    Main template-based view for listing remittances with filters.
    """
    model = Remittance
    template_name = "remittance/remittance_list.html"
    context_object_name = "remittances"
    paginate_by = PAGINATION_SIZE
    
    def get_queryset(self):
        if "workspace_id" not in self.kwargs:
            raise Http404("Workspace ID not found in URL parameters.")
        
        return get_remittances_with_filters(
            workspace_id=self.kwargs.get("workspace_id"),
            team_ids=self.request.GET.getlist("team"),
            statuses=self.request.GET.getlist("status"),
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
        return context
