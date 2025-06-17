from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
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
from apps.organizations.services import create_organization_with_owner
from apps.core.constants import PAGINATION_SIZE
from django.shortcuts import get_object_or_404
from typing import Any
from django.core.paginator import Paginator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required




# Create your views here.
def dashboard_view(request, organization_id):
    try:
        organization = Organization.objects.get(organization_id=organization_id)
        members_count = get_organization_members_count(organization)
        workspaces_count = get_workspaces_count(organization)
        teams_count = get_teams_count(organization)
        owner = organization.owner.user if organization.owner else None
        context = {
            "organization": organization,
            "members_count": members_count,
            "workspaces_count": workspaces_count,
            "teams_count": teams_count,
            "owner": owner,
        }
        return render(request, "organizations/dashboard.html", context)
    except Exception as e:
        messages.error(request, "Unable to load dashboard. Please try again later.")
        return render(request, "organizations/dashboard.html", {"organization": None})


@login_required
def home_view(request):
    try:
        organizations = get_user_organizations(request.user)
        paginator = Paginator(organizations, PAGINATION_SIZE)
        page = request.GET.get("page", 1)
        
        try:
            organizations = paginator.page(page)
        except PageNotAnInteger:
            organizations = paginator.page(1)
        except EmptyPage:
            organizations = paginator.page(paginator.num_pages)

        context = {
            "organizations": organizations,
        }
        template = "organizations/home.html"

        return render(request, template, context)

    except Exception as e:
        messages.error(request, "An error occurred while loading organizations")
        return render(request, "organizations/home.html", {"organizations": []})


# 

def create_organization_view(request):
    if request.method != "POST":
        form = OrganizationForm()
        return render(request, "organizations/partials/create_organization_form.html", {"form": form})
    else:
        form = OrganizationForm(request.POST)
        return render(request, "organizations/partials/create_organization_form.html", {"form": form})


def organization_overview_view(request, organization_id):
    organization = get_object_or_404(Organization, pk=organization_id)
    owner = organization.owner.user if organization.owner else None
    members = get_organization_members_count(organization)
    workspaces = get_workspaces_count(organization)
    teams = get_teams_count(organization)
    context = {
        "organization": organization,
        "members": members,
        "workspaces": workspaces,
        "teams": teams,
        "owner": owner,
    }
    return render(request, "organizations/organization_overview.html", context)

class OrganizationMemberListView(LoginRequiredMixin, ListView):
    model = OrganizationMember
    template_name = "organization_members/index.html"
    context_object_name = "members"
    paginate_by = PAGINATION_SIZE
    
    def dispatch(self, request, *args, **kwargs):
        # Get ORG ID from URL
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        query = OrganizationMember.objects.filter(organization=self.organization)
        return query

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "members"
        context["organization"] = self.organization
        return context

    def render_to_response(self, context: dict[str, Any], **response_kwargs: Any):
        if self.request.htmx:
            return render(
                self.request, "organization_members/partials/table.html", context
            )
        return super().render_to_response(context, **response_kwargs)
