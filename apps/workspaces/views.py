from django.shortcuts import render
from apps.workspaces.models import Workspace
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.workspaces.selectors import get_user_workspaces

# Create your views here.
class WorkspaceListView(ListView, LoginRequiredMixin):
    model = Workspace
    template_name = "workspaces\workspaces_list.html"
    context_object_name = "workspaces"

    def get_queryset(self):
        try:
            # Get all organization memberships of the current user
            return get_user_workspaces(self.request.user)
        except Exception as e:
            print(f"Error fetching workspaces: {str(e)}")
            return Workspace.objects.none()
