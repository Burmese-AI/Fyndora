# App Imports
from apps.teams.selectors import get_all_team_members, get_all_teams
from apps.organizations.models import Organization
from apps.organizations.selectors import get_user_org_membership
from apps.teams.models import Team
from apps.teams.forms import TeamCreationForm
from apps.teams.services import (create_team_for_organization,)

# Django Imports
from django.urls import reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render

# Create your views here.
class TeamListView(ListView, LoginRequiredMixin):
    model = Team
    template_name = "teams/index.html"
    context_object_name = "teams"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["teams"] = get_all_teams()
        return context

    def get_queryset(self):
        return get_all_teams()

class TeamCreateView(CreateView, LoginRequiredMixin):
    model = Team
    form_class = TeamCreationForm
    template_name = "teams/partials/form_teamcreation.html"

    def __init__(self):
        self.organization = None

    def dispatch(self, request, *args, **kwargs):
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        self.org_member = get_user_org_membership(self.request.user, self.organization)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = TeamCreationForm()
        context = {"form": form, "organization": self.organization}
        return render(request, "teams/components/form_teamcreation.html", context=context)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["org_member"] = self.org_member
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            context["is_oob"] = True
        return context
    
    def form_valid(self, form):
        try:
            create_team_for_organization(
                form=form, org_member=self.org_member, organization=self.organization
            )
            messages.success(self.request, "Team added successfully")
            if self.request.htmx:
                return self._render_htmx_success_response()
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"An error occurred: {str(e)}")
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        try:
            messages.error(self.request, "Adding a new team failed")
            if self.request.htmx:
                return self._render_htmx_error_response(form)
            return super().form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"An error occurred: {str(e)}")
            return self.form_invalid(form)
    
    def _render_htmx_success_response(self):
        pass
    
    def _render_htmx_error_response(self, form):
        pass
    
        