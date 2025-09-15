from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render
from apps.core.services.organizations import (
    get_organization_by_id,
)
from .constants import AuditActionType
from .selectors import AuditLogSelector, get_audit_log_by_id
from .models import AuditTrail
User = get_user_model()


# class AuditLogListView(LoginRequiredMixin, ListView):
#     """
#     A view to display a list of audit trail logs with filtering and search capabilities.
#     """

#     model = AuditTrail
#     template_name = "auditlog/index.html"
#     context_object_name = "audit_logs"
#     paginate_by = 20

#     def get_queryset(self):
#         # Use the selector to fetch and filter the queryset
#         return AuditLogSelector.get_audit_logs_with_filters(
#             user_id=self.request.GET.get("user"),
#             action_type=self.request.GET.get("action_type"),
#             start_date=self.request.GET.get("start_date"),
#             end_date=self.request.GET.get("end_date"),
#             target_entity_id=self.request.GET.get("target_entity_id"),
#             target_entity_type=self.request.GET.get("target_entity_type"),
#             search_query=self.request.GET.get("q"),
#         )

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)

#         # Provide data for filter dropdowns
#         context["users"] = User.objects.all().order_by("username")
#         context["action_types"] = AuditActionType.choices
#         context["entity_types"] = ContentType.objects.all()

#         # Create a copy of the GET parameters to preserve filters in pagination
#         filters = self.request.GET.copy()
#         if "page" in filters:
#             filters.pop("page")

#         # Pass current filter values to the template for display
#         context["current_filters"] = filters
#         context["search_query"] = self.request.GET.get("q", "")

#         return context


def auditlog_list_view(request, organization_id):
    try:
        # Get organization
        organization = get_organization_by_id(organization_id)

        # Get filter parameters from request
        user_id = request.GET.get("user")
        action_type = request.GET.get("action_type")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        target_entity_id = request.GET.get("target_entity_id")
        target_entity_type = request.GET.get("target_entity_type")
        search_query = request.GET.get("q")
        security_related_only = request.GET.get("security_related") == "on"
        critical_actions_only = request.GET.get("critical_actions") == "on"
        exclude_system_actions = request.GET.get("exclude_system") == "on"

        # Convert date strings to datetime objects if provided
        start_date_obj = None
        end_date_obj = None
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                pass
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                pass

        # Get audit logs using the selector
        audit_logs = AuditLogSelector.get_audit_logs_with_filters(
            organization_id=organization_id,
            user_id=user_id,
            action_type=action_type,
            start_date=start_date_obj,
            end_date=end_date_obj,
            target_entity_id=target_entity_id,
            target_entity_type=target_entity_type,
            search_query=search_query,
            security_related_only=security_related_only,
            critical_actions_only=critical_actions_only,
            exclude_system_actions=exclude_system_actions,
        )

        # Pagination
        from django.core.paginator import Paginator

        paginator = Paginator(audit_logs, 20)  # 20 items per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Get filter options for dropdowns
        users = User.objects.all().order_by("username")
        action_types = AuditActionType.choices
        entity_types = ContentType.objects.all().order_by("model")

        # Create a copy of the GET parameters to preserve filters in pagination
        filters = request.GET.copy()
        if "page" in filters:
            filters.pop("page")

        context = {
            "organization": organization,
            "audit_logs": page_obj,
            "users": users,
            "action_types": action_types,
            "entity_types": entity_types,
            "current_filters": filters,
            "search_query": search_query or "",
            "security_related": security_related_only,
            "critical_actions": critical_actions_only,
            "exclude_system": exclude_system_actions,
        }

        # Check if this is an HTMX request
        if request.headers.get('HX-Request'):
            return render(request, "auditlog/audit_logs_table.html", context)
        else:
            return render(request, "auditlog/index.html", context)

    except Exception as e:
        # Handle any errors gracefully
        context = {
            "organization": get_organization_by_id(organization_id),
            "error": str(e),
            "audit_logs": [],
        }
        
        # Check if this is an HTMX request for error handling
        if request.headers.get('HX-Request'):
            return render(request, "auditlog/audit_logs_table.html", context)
        else:
            return render(request, "auditlog/index.html", context)


def audit_detail_view(request, organization_id, audit_log_id):
    try:
        organization = get_organization_by_id(organization_id)
        audit_log = get_audit_log_by_id(audit_log_id)
        context = {
            "organization": organization,
            "audit_log": audit_log,
        }
        print("i am here")
        print(context)
        return render(request, "auditlog/audit_log_detail_modal.html", context)
    except Exception as e:
        context = {
            "organization": organization,
            "error": str(e),
            "audit_log": None,
        }
        return render(request, "auditlog/index.html", context)
  