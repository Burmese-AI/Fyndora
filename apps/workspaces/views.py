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
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.workspaces.selectors import get_workspace_by_id, get_orgMember_by_user_id_and_organization_id
from apps.workspaces.services import update_workspace_from_form


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
    orgMember = get_orgMember_by_user_id_and_organization_id(request.user.user_id, organization_id)
    print(orgMember)
    if request.method == "POST":
        form = WorkspaceForm(request.POST, organization=organization)
        try:
            if form.is_valid():
                create_workspace_from_form(form=form, orgMember=orgMember, organization=organization)
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
        "workspaces/workspace_create_form.html",
        context,
    )


def edit_workspace(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        
        if not workspace or not organization:
            messages.error(request, "Workspace or organization not found.")
            return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")

        if request.method == "POST":
            form = WorkspaceForm(request.POST, instance=workspace)
            try:
                if form.is_valid():
                    update_workspace_from_form(form=form, workspace=workspace)
                    messages.success(request, "Workspace updated successfully.")
                    return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
                else:
                    messages.error(request, "Invalid form data.")
            except WorkspaceUpdateError as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            form = WorkspaceForm(instance=workspace)
            
        context = {
            "form": form,
            "organization": organization,
        }
        return render(request, "workspaces/workspace_edit_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")