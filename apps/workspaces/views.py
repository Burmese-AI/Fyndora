from apps.workspaces.models import Workspace
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.workspaces.selectors import get_user_workspaces
from apps.workspaces.forms import WorkspaceForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect
from apps.workspaces.services import create_workspace_with_admin
from apps.workspaces.exceptions import WorkspaceCreationError
from apps.organizations.models import Organization


# Create your views here.
class WorkspaceListView(ListView, LoginRequiredMixin):
    model = Workspace
    template_name = "workspaces/workspaces_list.html"
    context_object_name = "workspaces"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = Organization.objects.get(organization_id=self.kwargs["organization_id"])
        return context

    def get_queryset(self):
        return get_user_workspaces(self.request.user)


@login_required
def create_workspace(request, organization_id):
    form = WorkspaceForm()
    organization = Organization.objects.get(organization_id=organization_id)
    print(organization_id)
    context = {
        "form": form,
        "organization": organization
    }
    return render(request, "workspaces/workspace_form.html", context)