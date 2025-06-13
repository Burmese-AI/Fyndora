from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from apps.organizations.models import Organization
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


# Create your views here.
def test_view(request):
    return render(request, "organizations/dashboard.html")


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


@login_required
def create_organization(request):
    try:
        if request.method == "POST":
            form = OrganizationForm(request.POST)
            if form.is_valid():
                try:
                    create_organization_with_owner(form=form, user=request.user)

                    if request.headers.get("HX-Request"):
                        messages.success(request, "Organization created successfully!")
                        return HttpResponseClientRedirect("/")
                except OrganizationCreationError as e:
                    messages.error(request, str(e))
                    if request.headers.get("HX-Request"):
                        return HttpResponseClientRedirect("/")
                    return render(
                        request, "organizations/organization_form.html", {"form": form}
                    )
        else:
            form = OrganizationForm()
        return render(request, "organizations/organization_form.html", {"form": form})
    except Exception:
        if request.headers.get("HX-Request"):
            messages.error(
                request, "An unexpected error occurred. Please try again later."
            )
            return HttpResponseClientRedirect("/")
        raise OrganizationCreationError(
            "An unexpected error occurred. Please try again later."
        )
