from django.shortcuts import render

from apps.core.constants import PAGINATION_SIZE

from .constants import RemittanceStatus
from apps.core.selectors import (
    get_organization_by_id,
    get_workspaces_under_organization,
)
from apps.remittance.selectors import get_remittances_under_organization
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from .services import remittance_confirm_payment
from .models import Remittance
from django.contrib import messages
from .exceptions import RemittanceConfirmPaymentException
from django.template.loader import render_to_string
from django.http import HttpResponse
from apps.remittance.utils import can_confirm_remittance_payment
from apps.core.utils import permission_denied_view


# developed by THA for the remittance list by each workspace team
# this is display the remittance list by each workspace team (due amount , paid amount , status , etc)
def remittance_list_view(request, organization_id):
    """
    View to list remittances for a specific workspace team.
    """
    try:
        filtered_workspace_id = request.GET.get("workspace_id")
        filtered_status = request.GET.get("status")
        search_query = request.GET.get("q")  # Add search functionality

        # Convert empty string to None for proper filtering
        if filtered_workspace_id == "":
            filtered_workspace_id = None
        if filtered_status == "":
            filtered_status = None
        if search_query == "":
            search_query = None

        # Use Q objects in the selector
        remittances = get_remittances_under_organization(
            organization_id=organization_id,
            workspace_id=filtered_workspace_id,
            status=filtered_status,
            search_query=search_query,
        )

        organization = get_organization_by_id(organization_id)  # for context
        workspaces = get_workspaces_under_organization(
            organization_id
        )  # for dropdown filter

        # Handle case where remittances is None
        if remittances is None:
            remittances = []

        paginator = Paginator(remittances, PAGINATION_SIZE)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        context = {
            "organization": organization,
            "remittances": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "page_obj": page_obj,
            "paginator": paginator,
            "workspaces": workspaces,  # for dropdown filter
            "selected_workspace_id": filtered_workspace_id,  # to maintain selected state
            "selected_status": filtered_status,  # to maintain selected status
            "search_query": search_query,  # to maintain search state
            "remittance_status": RemittanceStatus.choices,  # for dropdown filter
        }
        # if hx-request is true, return the partial template and for the full template, return the full template
        if request.headers.get("HX-Request"):
            return render(
                request, "remittance/components/remittance_table.html", context
            )
        return render(request, "remittance/index.html", context)
    except Exception as e:
        # Handle any errors gracefully
        print(f"Error in remittance_list_view: {e}")
        context = {
            "organization": get_organization_by_id(organization_id),
            "remittances": [],
            "workspaces": get_workspaces_under_organization(organization_id) or [],
        }
        return render(request, "remittance/index.html", context)


def remittance_confirm_payment_view(request, organization_id, remittance_id):
    """
    View to confirm a remittance payment.
    """
    try:
       
        organization = get_organization_by_id(organization_id)
        remittance = get_object_or_404(Remittance, pk=remittance_id)
        if not can_confirm_remittance_payment(request.user, organization):
            return permission_denied_view(request, "You do not have permission to confirm this remittance payment.")

        if request.method == "POST":
            try:
                updated_remittance = remittance_confirm_payment(
                    remittance=remittance,
                    user=request.user,
                    organization_id=organization_id,
                )
                # if update remittance.confirmed_by is not None, for the message , we show confirmed message
                if updated_remittance.confirmed_by is not None:
                    messages.success(
                        request, "Remittance Payment Confirmed successfully"
                    )
                else:
                    # if update remittance.confirmed_by is None, for the message , we show updated message
                    messages.success(request, "Remittance Payment Updated successfully")
                context = {
                    "organization": organization,
                    "remittances": get_remittances_under_organization(
                        organization_id=organization_id
                    ),
                    "is_oob": True,
                }
                message_html = render_to_string(
                    "includes/message.html", context=context, request=request
                )
                remittance_table_html = render_to_string(
                    "remittance/components/remittance_table.html",
                    context=context,
                    request=request,
                )
                response = HttpResponse(f"{message_html} {remittance_table_html}")
                response["HX-trigger"] = "success"
                return response

            except RemittanceConfirmPaymentException as e:
                messages.error(request, str(e))
                context = {
                    "organization": organization,
                    "remittances": get_remittances_under_organization(
                        organization_id=organization_id
                    ),
                    "is_oob": True,
                }
                message_html = render_to_string(
                    "includes/message.html", context=context, request=request
                )
                remittance_table_html = render_to_string(
                    "remittance/components/remittance_table.html",
                    context=context,
                    request=request,
                )
                response = HttpResponse(f"{message_html} {remittance_table_html}")
                response["HX-trigger"] = "error"
                return response
        else:
            # if the request is not a POST request, then we need to render the form template
            context = {
                "remittance": remittance,
                "organization": organization,
            }
            return render(
                request,
                "remittance/components/remittance_form.html",
                context,
            )
    except Exception as e:
        messages.error(request, "Error in remittance_confirm_payment_view")
        print(f"Error in remittance_confirm_payment_view: {e}")
        return redirect("remittance_list", organization_id=organization_id)


# this view will not be currently used
# class RemittanceListView(LoginRequiredMixin, ListView):
#     """
#     Main template-based view for listing remittances with filters.
#     """

#     model = Remittance
#     template_name = "remittance/index.html"
#     context_object_name = "remittances"
#     paginate_by = PAGINATION_SIZE

#     def get_template_names(self):
#         # If the request is from htmx, return the partial template
#         if self.request.META.get("HTTP_HX_REQUEST"):
#             return ["remittance/remittance_list.html"]
#         # Otherwise, return the full template
#         return [self.template_name]

#     def get_queryset(self):
#         if "workspace_id" not in self.kwargs:
#             raise Http404("Workspace ID not found in URL parameters.")

#         return get_remittances_with_filters(
#             workspace_id=self.kwargs.get("workspace_id"),
#             team_id=self.request.GET.get("team"),
#             status=self.request.GET.get("status"),
#             start_date=self.request.GET.get("start_date"),
#             end_date=self.request.GET.get("end_date"),
#             search=self.request.GET.get("q"),
#         )

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         workspace_id = self.kwargs.get("workspace_id")

#         # Get current workspace and add it to context
#         workspace = Workspace.objects.filter(pk=workspace_id).first()
#         context["workspace"] = workspace

#         # Get all teams and statuses for filter dropdowns
#         if workspace:
#             context["all_teams"] = Team.objects.filter(
#                 workspace_teams__workspace=workspace
#             ).order_by("title")
#         else:
#             context["all_teams"] = Team.objects.none()

#         context["all_statuses"] = RemittanceStatus.choices

#         # Preserve existing filters for pagination and search query
#         context["current_filters"] = self.request.GET.copy()
#         if "page" in context["current_filters"]:
#             context["current_filters"].pop("page")
#         context["search_query"] = self.request.GET.get("q", "")
#         context["workspace_id"] = self.kwargs.get("workspace_id")
#         return context

# #this view will not be currently used
# class RemittanceConfirmPaymentView(LoginRequiredMixin, View):
#     """
#     View to handle the confirmation of a remittance payment.
#     """

#     def post(self, request, *args, **kwargs):
#         remittance_id = kwargs.get("remittance_id")
#         remittance = get_object_or_404(Remittance, pk=remittance_id)

#         try:
#             updated_remittance = remittance_confirm_payment(
#                 remittance=remittance, user=request.user
#             )

#             context = {
#                 "remittance": updated_remittance,
#                 "workspace": updated_remittance.workspace,
#             }
#             return render(request, "remittance/remittance_row.html", context)

#         except (PermissionDenied, ValidationError) as e:
#             messages.error(request, str(e))
#             response = HttpResponse(status=204)
#             response["HX-Refresh"] = "true"
#             return response
