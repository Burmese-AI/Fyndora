from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
from apps.organizations.models import Organization
from apps.organizations.selectors import get_user_organizations, get_organization_members_count, get_workspaces_count, get_teams_count


# Create your views here.


class HomeView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/home.html"
    context_object_name = "organizations"

    def get_queryset(self):
        try:
            return get_user_organizations(self.request.user)
        except Exception as e:
            # Log the error here if you have a logging system
            raise PermissionDenied("Unable to fetch organizations. Please try again later.")


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "organizations/organization_detail.html"
    context_object_name = "organization"
    

    def get_queryset(self):
        try:
            return get_user_organizations(self.request.user)
        except Exception as e:
            # Log the error here if you have a logging system
            raise PermissionDenied("Unable to fetch organization details. Please try again later.")

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context["members"] = get_organization_members_count(self.object)
            context["workspaces"] = get_workspaces_count(self.object)
            context["teams"] = get_teams_count(self.object)
            return context
        except Exception as e:
            # Log the error here if you have a logging system
            raise PermissionDenied("Unable to fetch organization context data. Please try again later.")