from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.views.generic import ListView

from .constants import AuditActionType
from .models import AuditTrail
from .selectors import get_audit_logs_for_workspace_with_filters

User = get_user_model()


class AuditLogListView(LoginRequiredMixin, ListView):
    """
    A view to display a list of audit trail logs with filtering and search capabilities.
    """

    model = AuditTrail
    template_name = "auditlog/index.html"
    context_object_name = "audit_logs"
    paginate_by = 20

    def get_queryset(self):
        # Use the selector to fetch and filter the queryset
        return get_audit_logs_for_workspace_with_filters(
            user_id=self.request.GET.get("user"),
            action_type=self.request.GET.get("action_type"),
            start_date=self.request.GET.get("start_date"),
            end_date=self.request.GET.get("end_date"),
            target_entity_id=self.request.GET.get("target_entity_id"),
            target_entity_type=self.request.GET.get("target_entity_type"),
            search_query=self.request.GET.get("q"),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Provide data for filter dropdowns
        context["users"] = User.objects.all().order_by("username")
        context["action_types"] = AuditActionType.choices
        context["entity_types"] = ContentType.objects.all()

        # Create a copy of the GET parameters to preserve filters in pagination
        filters = self.request.GET.copy()
        if "page" in filters:
            filters.pop("page")

        # Pass current filter values to the template for display
        context["current_filters"] = filters
        context["search_query"] = self.request.GET.get("q", "")

        return context
