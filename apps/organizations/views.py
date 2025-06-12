from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from apps.organizations.models import Organization, OrganizationMember
from apps.organizations.selectors import (
    get_user_organizations,
    get_organization_members_count,
    get_workspaces_count,
    get_teams_count,
)
from apps.organizations.forms import OrganizationForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect

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


@login_required
def organization_create(request):
    try:
        if request.method == "POST":
            form = OrganizationForm(request.POST)
            if form.is_valid():
                organization = form.save(commit=False)
                organization.save()
                # Create organization member for the owner
                OrganizationMember.objects.create(
                    organization=organization,
                    user=request.user,
                    is_active=True
                )
                
                organization.owner= OrganizationMember.objects.get(organization=organization, user=request.user)
                organization.save()

                if request.headers.get('HX-Request'):
                    # Return a success response for HTMX
                    messages.success(request, "Organization created successfully!")
                    return HttpResponseClientRedirect("/")
        else:
            form = OrganizationForm()
        return render(request, "organizations/organization_form.html", {"form": form})
    except Exception as e:
        if request.headers.get('HX-Request'):
            messages.error(request, "Unable to create organization. Please try again later.")
            return HttpResponseClientRedirect("/")
        raise PermissionDenied("Unable to create organization. Please try again later.")
