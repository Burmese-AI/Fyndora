from django.views.generic import ListView
from apps.teams.selectors import get_all_team_members
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from apps.teams.models import Team
from apps.workspaces.selectors import get_organization_by_id

# Create your views here.
def teams_view(request, organization_id):
    print(organization_id)
    teams = Team.objects.filter(organization_id=organization_id)
    organization = get_organization_by_id(organization_id)
    context = {
        "teams": teams,
        "organization": organization
    }
    return render(request, "teams/index.html", context)