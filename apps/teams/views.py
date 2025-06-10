from django.shortcuts import render
from django.views.generic import ListView
from .models import Team

# Create your views here.
class TeamListView(ListView):
    model = Team
    template_name = 'teams/team_list.html'
    context_object_name = 'teams'

    def get_queryset(self):
        return Team.objects.all()