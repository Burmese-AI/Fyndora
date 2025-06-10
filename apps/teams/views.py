from django.shortcuts import render
from django.views.generic import ListView
from apps.workspaces.models import WorkspaceTeam

# Create your views here.
class TeamListView(ListView):
    model = WorkspaceTeam
    template_name = 'teams/team_list.html'
    context_object_name = 'teams'
    print(WorkspaceTeam.objects.all())

    def get_queryset(self):
        return WorkspaceTeam.objects.all()