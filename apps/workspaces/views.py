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
from apps.workspaces.selectors import (
    get_workspace_by_id,
    get_orgMember_by_user_id_and_organization_id,
)
from apps.workspaces.services import update_workspace_from_form
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.views.generic.edit import FormView



# Create your views here.
class WorkspaceListView(
    ListView,
    LoginRequiredMixin,
):
    model = Workspace
    template_name = "workspaces/index.html"
    context_object_name = "workspaces"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = Organization.objects.get(
            organization_id=self.kwargs["organization_id"]
        )
        return context

    def get_queryset(self):
        return get_user_workspaces_under_organization(self.kwargs["organization_id"])



class CreateWorkspaceView(LoginRequiredMixin, FormView):
    form_class = WorkspaceForm
    template_name = "workspaces/partials/create_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_organization_by_id(kwargs['organization_id'])
        self.orgMember = get_orgMember_by_user_id_and_organization_id(
            request.user.user_id, self.organization.pk
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass organization into form."""
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.organization
        return kwargs

    def form_valid(self, form):
        """Save and handle messages, then respond appropriately."""
        try:
            create_workspace_from_form(
                form=form, orgMember=self.orgMember, organization=self.organization
            )
            messages.success(self.request, "Workspace created successfully.")
            if self.request.headers.get("HX-Request"):
                organization = self.organization
                workspaces = get_user_workspaces_under_organization(organization.pk)
                context = {
                    "workspaces": workspaces,
                    "organization": organization,
                    "is_oob": True,
                }
                message_html = render_to_string("includes/message.html", context=context, request=self.request)
                workspace_display_html = render_to_string("workspaces/partials/workspaces_display.html", context=context, request=self.request)
                
                return HttpResponse(f"{message_html} {workspace_display_html}")
        except WorkspaceCreationError as e:
            messages.error(self.request, f"An error occurred: {str(e)}")
        
        context = {
            "form": form,
            "organization": self.organization,
        }
        return self.render_to_response(context)

    def form_invalid(self, form):
        """Handle form validation failure with messages and proper rendering."""
        messages.error(self.request, "Invalid form data.")
        context = {
            "form": form,
            "is_oob": True
        }
        message_html = render_to_string("includes/message.html", context=context, request=self.request)
        modal_html = render_to_string("workspaces/partials/create_form.html", context=context, request=self.request)
        return HttpResponse(f"{message_html} {modal_html}")

    def get_context_data(self, **kwargs):
        """Add organization to context for GET requests."""
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        return context



def edit_workspace(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)

        if not workspace or not organization:
            messages.error(request, "Workspace or organization not found.")
            return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")

        if request.method == "POST":
            form = WorkspaceForm(
                request.POST, instance=workspace, organization=organization
            )
            try:
                if form.is_valid():
                    update_workspace_from_form(form=form, workspace=workspace)
                    workspaces = get_user_workspaces_under_organization(organization_id)
                    context = {
                        "workspaces": workspaces,
                        "organization": organization,
                    }
                    print(workspaces)
                    messages.success(request, "Workspace updated successfully.")
                    return render(request, "workspaces/main_content.html", context)
                else:
                    response = render(request, "workspaces/workspace_edit_form.html", {"form": form})
                    response["HX-Retarget"] = "#workspace-edit-modal"
                    response["HX-Reswap"] = "innerHTML"
                    messages.error(request, "Invalid form data.")
                    return response
            except WorkspaceUpdateError as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            form = WorkspaceForm(instance=workspace, organization=organization)

        context = {
            "form": form,
            "organization": organization,
        }
        return render(request, "workspaces/workspace_edit_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


def delete_workspace(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)

        if not workspace or not organization:
            messages.error(request, "Workspace or organization not found.")
            return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")

        # Immediately delete on any request
        workspace.delete()
        messages.success(request, "Workspace deleted successfully.")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
