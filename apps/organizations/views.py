from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from apps.organizations.models import Organization, OrganizationMember
from apps.organizations.selectors import (
    get_user_organizations,
    get_organization_members_count,
    get_workspaces_count,
    get_teams_count,
)
from apps.organizations.forms import OrganizationForm
from django.shortcuts import render
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect
from apps.organizations.services import create_organization_with_owner
from apps.organizations.exceptions import OrganizationCreationError
from apps.core.constants import PAGINATION_SIZE
from django.shortcuts import get_object_or_404
from typing import Any


# Create your views here.
def dashboard_view(request, organization_id):
    print(organization_id)
    organization = Organization.objects.get(organization_id=organization_id)
    print(organization)
    context = {"organization": organization}
    return render(request, "organizations/dashboard.html", context)


def home_view(request):
    organizations = get_user_organizations(request.user)
    form = OrganizationForm()
    context = {"organizations": organizations, "form": form}
  
    return render(request, "organizations/home.html", context)

def create_organization_view(request):
    form = OrganizationForm()

    if request.method == "POST":
        form = OrganizationForm(request.POST)
        if form.is_valid():
           create_organization_with_owner(form=form, user=request.user)
           context = {"organizations": get_user_organizations(request.user), "form": form}
           messages.success(request, "Organization created successfully!")
           response = render(request, "organizations/partials/organization_card.html", context)
           response["HX-Trigger"] = "org-creation-success"
           return response
      
    
       

class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "organizations/organization_detail.html"
    context_object_name = "organization"

    def get_queryset(self):
        try:
            return get_user_organizations(self.request.user)
        except Exception:
            # Log the error here if you have a logging system
            raise PermissionDenied(
                "Unable to fetch organization details. Please try again later."
            )

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context["members"] = get_organization_members_count(self.object)
            context["workspaces"] = get_workspaces_count(self.object)
            context["teams"] = get_teams_count(self.object)
            return context
        except Exception:
            # Log the error here if you have a logging system
            raise PermissionDenied(
                "Unable to fetch organization context data. Please try again later."
            )




class OrganizationMemberListView(LoginRequiredMixin, ListView):
    model = OrganizationMember
    template_name = "organization_members/index.html"
    context_object_name = "members"
    paginate_by = PAGINATION_SIZE

    def get_queryset(self):
        organization = get_object_or_404(
            Organization, pk=self.kwargs["organization_id"]
        )
        query = OrganizationMember.objects.filter(organization=organization)
        return query

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "members"
        return context

    def render_to_response(self, context: dict[str, Any], **response_kwargs: Any):
        if self.request.htmx:
            return render(
                self.request, "organization_members/partials/table.html", context
            )
        return super().render_to_response(context, **response_kwargs)


# View to partially render the members section
# View to partially render the invitations section
# View to partially render the members table
# View to partially render the invitations table
# View to open a create invitation modal
