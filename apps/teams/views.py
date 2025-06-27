from django.views.generic import ListView
from apps.teams.selectors import get_all_team_members
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from apps.teams.models import Team
from apps.core.services.organizations import get_organization_by_id
from django.shortcuts import redirect
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect
from apps.workspaces.models import WorkspaceTeam
from apps.teams.forms import TeamForm

# Create your views here.
def teams_view(request, organization_id):
    try:
        teams = Team.objects.filter(organization_id=organization_id)
        for team in teams:
            attached_workspaces = WorkspaceTeam.objects.filter(team_id=team.team_id)
            team.attached_workspaces = attached_workspaces
        print(attached_workspaces)
        organization = get_organization_by_id(organization_id)
        context = {
            "teams": teams,
            "organization": organization,
        }
        return render(request, "teams/index.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/teams/")
    
def create_team_view(request, organization_id):
    try:
        organization = get_organization_by_id(organization_id)
        if request.method == "POST":
            form = TeamForm(request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseClientRedirect(f"/{organization_id}/teams/")
        else:
            form = TeamForm()
            context = {
                "form": form,
                "organization": organization,
            }
            return render(request, "teams/partials/create_team_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/teams/")