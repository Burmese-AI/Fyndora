from apps.workspaces.models import Workspace
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.workspaces.selectors import get_user_workspaces
from apps.workspaces.forms import WorkspaceForm
from django.shortcuts import render, redirect

# Create your views here.
class WorkspaceListView(ListView, LoginRequiredMixin):
    model = Workspace
    template_name = "workspaces/workspaces_list.html"
    context_object_name = "workspaces"

    def get_queryset(self):
        return get_user_workspaces(self.request.user)


def create_workspace(request):
   form = WorkspaceForm();
   context = {
      "form": form
   }
   return render(request, "workspaces/workspace_form.html", context)