from apps.workspaces.models import Workspace
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.workspaces.forms import WorkspaceForm
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.organizations.models import Organization
from django_htmx.http import HttpResponseClientRedirect
from apps.workspaces.selectors import (
    get_organization_by_id,
    get_user_workspaces_under_organization,
)
from apps.workspaces.services import create_workspace_from_form
from django.contrib import messages
from apps.workspaces.exceptions import WorkspaceCreationError
from apps.workspaces.selectors import get_workspace_by_id


# Create your views here.
class WorkspaceListView(
    ListView,
    LoginRequiredMixin,
):
    model = Workspace
    template_name = "workspaces/workspaces_list.html"
    context_object_name = "workspaces"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = Organization.objects.get(
            organization_id=self.kwargs["organization_id"]
        )
        return context

    def get_queryset(self):
        return get_user_workspaces_under_organization(self.kwargs["organization_id"])


@login_required
def create_workspace(request, organization_id):
    organization = get_organization_by_id(organization_id)
    if request.method == "POST":
        form = WorkspaceForm(request.POST, organization=organization)
        try:
            if form.is_valid():
                create_workspace_from_form(form=form, organization=organization)
                messages.success(request, "Workspace created successfully.")
                if request.headers.get("HX-Request"):
                    return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
            else:
                messages.error(request, "Invalid form data.")
        except WorkspaceCreationError as e:
            messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = WorkspaceForm(request.POST or None, organization=organization)
    context = {
        "form": form,
        "organization": organization,
    }
    return render(
        request,
        "workspaces/workspace_form.html",
        context,
    )


def edit_workspace(request, organization_id, workspace_id):
    workspace = get_workspace_by_id(workspace_id)
    organization = get_organization_by_id(organization_id)
    print(workspace)
    print(organization)
    if request.method == "POST":
        form = WorkspaceForm(request.POST, instance=workspace)
        if form.is_valid():
            form.save()
            messages.success(request, "Workspace updated successfully.")
            return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
    else:
        form = WorkspaceForm(instance=workspace)
    context = {
        "form": form,
        "organization": organization,
    }
    return render(request, "workspaces/workspace_form.html", context)