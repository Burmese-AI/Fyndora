from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
from apps.organizations.models import Organization
from apps.organizations.selectors import (
    get_user_organizations,
    get_organization_members_count,
    get_workspaces_count,
    get_teams_count,
)
from apps.organizations.forms import OrganizationForm
from django.shortcuts import render, redirect


# Create your views here.


class HomeView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/home.html"
    context_object_name = "organizations"

    def get_queryset(self):
        try:
            return get_user_organizations(self.request.user)
        except Exception:
            # Log the error here if you have a logging system
            raise PermissionDenied(
                "Unable to fetch organizations. Please try again later."
            )


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


# still working on creation not completed
def organization_create(request):
    try:
        if request.method == "POST":
            form = OrganizationForm(request.POST)
            if form.is_valid():
                organization = form.save(commit=False)
                organization.owner = request.user
                organization.save()
                return redirect("home")
        else:
            form = OrganizationForm()
        return render(request, "organizations/organization_create.html", {"form": form})
    except Exception:
        # Log the error here if you have a logging system
        raise PermissionDenied("Unable to create organization. Please try again later.")
