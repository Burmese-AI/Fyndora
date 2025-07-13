from apps.workspaces.forms import WorkspaceForm
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django_htmx.http import HttpResponseClientRedirect
from apps.workspaces.selectors import (
    get_organization_by_id,
)
from apps.workspaces.services import create_workspace_from_form
from django.contrib import messages
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.workspaces.selectors import (
    get_workspace_by_id,
    get_orgMember_by_user_id_and_organization_id,
    get_team_by_id,
)
from apps.workspaces.services import update_workspace_from_form
from django.template.loader import render_to_string
from django.http import HttpResponse
from apps.workspaces.forms import AddTeamToWorkspaceForm
from apps.workspaces.exceptions import AddTeamToWorkspaceError
from apps.workspaces.selectors import get_workspace_teams_by_workspace_id
from apps.workspaces.selectors import get_workspaces_with_team_counts
from apps.workspaces.services import remove_team_from_workspace, add_team_to_workspace
from django.contrib.auth.models import Group
from apps.workspaces.forms import ChangeWorkspaceTeamRemittanceRateForm
from apps.workspaces.selectors import (
    get_workspace_team_by_workspace_team_id,
    get_user_workspace_teams_under_organization,
)
from apps.workspaces.services import update_workspace_team_remittance_rate_from_form
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import WorkspaceTeam
from django.shortcuts import redirect
from apps.workspaces.selectors import get_single_workspace_with_team_counts


@login_required
def get_workspaces_view(request, organization_id):
    try:
        organization = get_organization_by_id(organization_id)
        workspaces = get_workspaces_with_team_counts(organization_id)
        return render(
            request,
            "workspaces/index.html",
            {
                "workspaces": workspaces,
                "organization": organization,
            },
        )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def create_workspace_view(request, organization_id):
    try:
        organization = get_organization_by_id(organization_id)
        orgMember = get_orgMember_by_user_id_and_organization_id(
            request.user.user_id, organization_id
        )
        if not orgMember.is_org_owner:
            messages.error(
                request,
                "You do not have permission to create a workspace in this organization.",
            )
            return HttpResponseClientRedirect("/403")

        if request.method == "POST":
            form = WorkspaceForm(request.POST, organization=organization)
            try:
                if form.is_valid():
                    create_workspace_from_form(
                        form=form, orgMember=orgMember, organization=organization
                    )
                    messages.success(request, "Workspace created successfully.")
                    if request.headers.get("HX-Request"):
                        organization = get_organization_by_id(organization_id)
                        workspaces = get_workspaces_with_team_counts(organization_id)
                        context = {
                            "workspaces": workspaces,
                            "organization": organization,
                            "is_oob": True,
                        }
                        message_html = render_to_string(
                            "includes/message.html", context=context, request=request
                        )
                        workspaces_grid_html = render_to_string(
                            "workspaces/partials/workspaces_grid.html",
                            context=context,
                            request=request,
                        )
                        response = HttpResponse(
                            f"{message_html} {workspaces_grid_html}"
                        )
                        response["HX-trigger"] = "success"
                        return response
                else:
                    messages.error(request, "Invalid form data.")
                    context = {"form": form, "is_oob": True}
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    modal_html = render_to_string(
                        "workspaces/partials/create_workspace_form.html",
                        context=context,
                        request=request,
                    )
                    return HttpResponse(f"{message_html} {modal_html}")
            except WorkspaceCreationError as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
        else:
            form = WorkspaceForm(request.POST or None, organization=organization)
        context = {
            "form": form,
            "organization": organization,
        }
        return render(
            request,
            "workspaces/partials/create_workspace_form.html",
            context,
        )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def edit_workspace_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        previous_workspace_admin = workspace.workspace_admin
        previous_operations_reviewer = workspace.operations_reviewer

        if not request.user.has_perm("change_workspace", workspace):
            messages.error(
                request, "You do not have permission to edit this workspace."
            )
            return HttpResponseClientRedirect("/403")

        if request.method == "POST":
            form = WorkspaceForm(
                request.POST, instance=workspace, organization=organization
            )
            try:
                if form.is_valid():
                    update_workspace_from_form(
                        form=form,
                        workspace=workspace,
                        previous_workspace_admin=previous_workspace_admin,
                        previous_operations_reviewer=previous_operations_reviewer,
                    )
                    workspace = get_single_workspace_with_team_counts(workspace_id)
                    print(f"DEBUG: workspace single testing: {workspace}")
                    context = {
                        "workspace": workspace,
                        "organization": organization,
                        "is_oob": True,
                    }

                    messages.success(request, "Workspace updated successfully.")
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    workspace_card_html = render_to_string(
                        "workspaces/partials/workspace_card.html",
                        context=context,
                        request=request,
                    )
                    response = HttpResponse(f"{message_html} {workspace_card_html}")
                    response["HX-trigger"] = "success"
                    return response
                else:
                    messages.error(request, "Invalid form data.")
                    context = {
                        "form": form,
                        "is_oob": True,
                        "organization": organization,
                    }
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    modal_html = render_to_string(
                        "workspaces/partials/edit_workspace_form.html",
                        context=context,
                        request=request,
                    )
                    return HttpResponse(f"{message_html} {modal_html}")
            except WorkspaceUpdateError as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
        else:
            form = WorkspaceForm(instance=workspace, organization=organization)

        context = {
            "form": form,
            "organization": organization,
        }
        return render(request, "workspaces/partials/edit_workspace_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def delete_workspace_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)

        if not request.user.has_perm("delete_workspace", workspace):
            messages.error(
                request, "You do not have permission to delete this workspace."
            )
            return HttpResponseClientRedirect("/403")

        if request.method == "POST":
            group_name = f"Workspace Admins - {workspace_id}"
            group = Group.objects.filter(name=group_name).first()
            group.delete()
            workspace.delete()
            messages.success(request, "Workspace deleted successfully.")
            organization = get_organization_by_id(organization_id)
            workspaces = get_workspaces_with_team_counts(organization_id)
            context = {
                "workspaces": workspaces,
                "organization": organization,
                "is_oob": True,
            }
            message_html = render_to_string(
                "includes/message.html", context=context, request=request
            )
            workspaces_grid_html = render_to_string(
                "workspaces/partials/workspaces_grid.html",
                context=context,
                request=request,
            )

            response = HttpResponse(f"{message_html} {workspaces_grid_html}")
            response["HX-trigger"] = "success"
            return response

        else:
            context = {
                "workspace": workspace,
                "organization": organization,
            }
        return render(
            request, "workspaces/partials/delete_workspace_form.html", context
        )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def add_team_to_workspace_view(request, organization_id, workspace_id):
    try:
        organization = get_organization_by_id(organization_id)
        workspace = get_workspace_by_id(workspace_id)

        if request.method == "POST":
            form = AddTeamToWorkspaceForm(
                request.POST, organization=organization, workspace=workspace
            )
            try:
                if form.is_valid():
                    add_team_to_workspace(
                        workspace_id,
                        form.cleaned_data["team"].team_id,
                        form.cleaned_data["custom_remittance_rate"],
                    )
                    workspace = get_single_workspace_with_team_counts(workspace_id)
                    context = {
                        "workspace": workspace,
                        "organization": organization,
                        "is_oob": True,
                    }
                    messages.success(request, "Team added to workspace successfully.")
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    workspace_card_html = render_to_string(
                        "workspaces/partials/workspace_card.html",
                        context=context,
                        request=request,
                    )
                    response = HttpResponse(f"{workspace_card_html} {message_html} ")
                    response["HX-trigger"] = "success"
                    return response
                else:
                    messages.error(request, "Invalid form data.")
                    context = {
                        "form": form,
                        "is_oob": True,
                    }
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    add_team_form_html = render_to_string(
                        "workspaces/partials/add_workspace_team_form.html",
                        context=context,
                        request=request,
                    )
                    response = HttpResponse(f"{add_team_form_html} {message_html}")
                    return response
            except AddTeamToWorkspaceError as e:
                messages.error(request, str(e))
                return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
        else:
            form = AddTeamToWorkspaceForm(organization=organization)
            context = {
                "form": form,
                "organization": organization,
                "workspace": workspace,
            }
            return render(
                request, "workspaces/partials/add_workspace_team_form.html", context
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def get_workspace_teams_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        workspace_teams = get_workspace_teams_by_workspace_id(workspace_id)

        context = {
            "workspace_teams": workspace_teams,
            "workspace": workspace,
            "organization": organization,
            "view": "teams",
            "hide_management_access": False,
        }
        return render(request, "workspace_teams/index.html", context)
    except Exception as e:
        print(f"DEBUG: An unexpected error occurred: {str(e)}")
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return render(request, "workspace_teams/index.html", context)


@login_required
def remove_team_from_workspace_view(request, organization_id, workspace_id, team_id):
    try:
        team = get_team_by_id(team_id)
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        if request.method == "POST":
            remove_team_from_workspace(workspace_id, team_id)
            messages.success(request, "Team removed from workspace successfully.")
            workspace_teams = get_workspace_teams_by_workspace_id(workspace_id)
            context = {
                "workspace_teams": workspace_teams,
                "workspace": workspace,
                "organization": organization,
                "is_oob": True,
            }
            workspace_team_grid_html = render_to_string(
                "workspace_teams/partials/workspace_teams_grid.html",
                context=context,
                request=request,
            )
            message_html = render_to_string(
                "includes/message.html", context=context, request=request
            )
            response = HttpResponse(f"{message_html} {workspace_team_grid_html}")
            response["HX-trigger"] = "success"
            return response
        else:
            return render(
                request,
                "workspace_teams/partials/remove_workspace_team_form.html",
                {"team": team, "workspace": workspace, "organization": organization},
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect(
            "get_workspace_teams",
            organization_id=organization_id,
            workspace_id=workspace_id,
        )


@login_required
def change_workspace_team_remittance_rate_view(
    request, organization_id, workspace_id, team_id, workspace_team_id
):
    try:
        workspace_team = get_workspace_team_by_workspace_team_id(workspace_team_id)
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        team = get_team_by_id(team_id)
        if request.method == "POST":
            form = ChangeWorkspaceTeamRemittanceRateForm(
                request.POST, instance=workspace_team
            )
            if form.is_valid():
                update_workspace_team_remittance_rate_from_form(
                    form=form, workspace_team=workspace_team, workspace=workspace
                )
                messages.success(request, "Remittance rate updated successfully.")
                workspace_team = get_workspace_team_by_workspace_team_id(
                    workspace_team_id
                )
                context = {
                    "workspace_team": workspace_team,
                    "workspace": workspace,
                    "organization": organization,
                    "is_oob": True,
                }
                workspace_team_card_html = render_to_string(
                    "workspace_teams/partials/workspace_team_card.html",
                    context=context,
                    request=request,
                )
                message_html = render_to_string(
                    "includes/message.html",
                    context=context,
                    request=request,
                )
                response = HttpResponse(f"{message_html} {workspace_team_card_html}")
                response["HX-trigger"] = "success"
                return response
            else:
                messages.error(request, "Invalid form data.")
                context = {
                    "form": form,
                    "workspace_team": workspace_team,
                    "organization": organization,
                    "team": team,
                    "workspace": workspace,
                    "is_oob": True,
                }
                modal_html = render_to_string(
                    "workspace_teams/partials/edit_workspace_team_remittance_form.html",
                    context=context,
                    request=request,
                )
                message_html = render_to_string(
                    "includes/message.html",
                    context=context,
                    request=request,
                )
                response = HttpResponse(f"{message_html} {modal_html}")
                return response
        else:
            form = ChangeWorkspaceTeamRemittanceRateForm(instance=workspace_team)
            context = {
                "form": form,
                "organization": organization,
                "workspace_team": workspace_team,
                "workspace": workspace,
                "team": team,
            }
            return render(
                request,
                "workspace_teams/partials/edit_workspace_team_remittance_form.html",
                context,
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(
            f"/{organization_id}/workspaces/{workspace_id}/teams"
        )


class SubmissionTeamListView(LoginRequiredMixin, ListView):
    model = WorkspaceTeam
    template_name = "workspace_teams/submitter_workspace_teams_index.html"
    paginate_by = 10
    context_object_name = "workspace_teams"

    def get_queryset(self):
        user = self.request.user
        org_id = self.kwargs["organization_id"]

        return get_user_workspace_teams_under_organization(org_id, user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = get_organization_by_id(self.kwargs["organization_id"])
        context["hide_management_access"] = True
        return context
