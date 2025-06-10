from django.views.generic import ListView
from apps.teams.selectors import get_all_team_members
from django.contrib.auth.mixins import LoginRequiredMixin


# Create your views here.
class TeamListView(ListView, LoginRequiredMixin):
    template_name = "teams/team_list.html"
    context_object_name = "teams"

    def get_queryset(self):
        return get_all_team_members()
