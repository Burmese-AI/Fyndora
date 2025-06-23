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


# from django.core.exceptions import PermissionDenied
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
                "You do not have permission to create workspaces in this organization.",
            )
            context = {
                "message": "You do not have permission to create workspaces in this organization.",
                "return_url": f"/{organization_id}/workspaces/",
            }
            response = render(
                request,
                "components/error_page.html",
                context,
            )
            response["HX-Retarget"] = "#right-side-content-container"
            return response
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
                        workspace_display_html = render_to_string(
                            "workspaces/partials/workspaces_display.html",
                            context=context,
                            request=request,
                        )
                        response = HttpResponse(
                            f"{message_html} {workspace_display_html}"
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
                        "workspaces/partials/create_form.html",
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
            "workspaces/partials/create_form.html",
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

        if not request.user.has_perm("change_workspace", workspace):
            messages.error(
                request, "You do not have permission to edit this workspace."
            )
            context = {
                "message": "You do not have permission to edit this workspace.",
                "return_url": f"/{organization_id}/workspaces/",
            }
            response = render(
                request,
                "components/error_page.html",
                context,
            )
            response["HX-Retarget"] = "#right-side-content-container"
            return response

        if request.method == "POST":
            form = WorkspaceForm(
                request.POST, instance=workspace, organization=organization
            )
            try:
                if form.is_valid():
                    update_workspace_from_form(form=form, workspace=workspace)
                    workspaces = get_workspaces_with_team_counts(organization_id)
                    context = {
                        "workspaces": workspaces,
                        "organization": organization,
                        "is_oob": True,
                    }

                    messages.success(request, "Workspace updated successfully.")
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    workspace_display_html = render_to_string(
                        "workspaces/partials/workspaces_display.html",
                        context=context,
                        request=request,
                    )
                    response = HttpResponse(f"{message_html} {workspace_display_html}")
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
                        "workspaces/partials/edit_form.html",
                        context=context,
                        request=request,
                    )
                    return HttpResponse(f"{message_html} {modal_html}")
            except WorkspaceUpdateError as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            form = WorkspaceForm(instance=workspace, organization=organization)

        context = {
            "form": form,
            "organization": organization,
        }
        return render(request, "workspaces/partials/edit_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


def delete_workspace_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)

        if not request.user.has_perm("delete_workspace", workspace):
            messages.error(
                request, "You do not have permission to delete this workspace."
            )
            context = {
                "message": "You do not have permission to delete this workspace.",
                "return_url": f"/{organization_id}/workspaces/",
            }
            response = render(
                request,
                "components/error_page.html",
                context,
            )
            response["HX-Retarget"] = "#right-side-content-container"
            return response
        if request.method == "POST":
            group_name = (
            f"Workspace Admins - {workspace_id}"
        )
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
            workspace_display_html = render_to_string(
                "workspaces/partials/workspaces_display.html",
                context=context,
                request=request,
            )

            response = HttpResponse(f"{message_html} {workspace_display_html}")
            response["HX-trigger"] = "success"
            return response

        else:
            context = {
                "workspace": workspace,
                "organization": organization,
            }
        return render(request, "workspaces/partials/delete_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


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
                        workspace_id, form.cleaned_data["team"].team_id
                    )
                    workspaces = get_workspaces_with_team_counts(organization_id)
                    context = {
                        "workspaces": workspaces,
                        "organization": organization,
                        "is_oob": True,
                    }
                    messages.success(request, "Team added to workspace successfully.")
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    workspace_display_html = render_to_string(
                        "workspaces/partials/workspaces_display.html",
                        context=context,
                        request=request,
                    )
                    response = HttpResponse(f"{workspace_display_html} {message_html} ")
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
                        "workspaces/partials/add_team_form.html",
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
            return render(
                request, "workspaces/partials/add_team_form.html", {"form": form}
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


def get_workspace_teams_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        workspace_teams = get_workspace_teams_by_workspace_id(workspace_id)
        context = {
            "workspace_teams": workspace_teams,
            "workspace": workspace,
        }
        return render(request, "workspaces/workspace_teams_main.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


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
            workspace_team_display_html = render_to_string(
                "workspaces/partials/workspaces_team_display.html",
                context=context,
                request=request,
            )
            message_html = render_to_string(
                "includes/message.html", context=context, request=request
            )
            response = HttpResponse(f"{message_html} {workspace_team_display_html}")
            response["HX-trigger"] = "success"
            return response
        else:
            return render(
                request,
                "workspaces/partials/workspace_team_remove_form.html",
                {"team": team, "workspace": workspace, "organization": organization},
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


def test1_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        context = {
            "workspace": workspace,
        }
        return render(request, "workspaces/test1.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
