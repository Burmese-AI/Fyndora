from apps.workspaces.forms import WorkspaceForm
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
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
from apps.workspaces.forms import AddTeamToWorkspaceForm
from apps.workspaces.models import WorkspaceTeam
from apps.workspaces.exceptions import AddTeamToWorkspaceError
from apps.workspaces.selectors import get_workspace_teams_by_workspace_id


def get_workspaces(request, organization_id):
    organization = get_organization_by_id(organization_id)
    workspaces = get_user_workspaces_under_organization(organization_id)
    for workspace in workspaces:
        workspace.teams_count = get_workspace_teams_by_workspace_id(
            workspace.workspace_id
        ).count()
    return render(
        request,
        "workspaces/index.html",
        {
            "workspaces": workspaces,
            "organization": organization,
        },
    )


@login_required
def create_workspace(request, organization_id):
    organization = get_organization_by_id(organization_id)
    orgMember = get_orgMember_by_user_id_and_organization_id(
        request.user.user_id, organization_id
    )
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
                    workspaces = get_user_workspaces_under_organization(organization_id)
                    for workspace in workspaces:
                        workspace.teams_count = get_workspace_teams_by_workspace_id(
                            workspace.workspace_id
                        ).count()
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


@login_required
def edit_workspace(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)

        if request.method == "POST":
            form = WorkspaceForm(
                request.POST, instance=workspace, organization=organization
            )
            try:
                if form.is_valid():
                    update_workspace_from_form(form=form, workspace=workspace)
                    workspaces = get_user_workspaces_under_organization(organization_id)
                    for workspace in workspaces:
                        workspace.teams_count = get_workspace_teams_by_workspace_id(
                            workspace.workspace_id
                        ).count()
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


def delete_workspace(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        if request.method == "POST":
            workspace.delete()
            messages.success(request, "Workspace deleted successfully.")
            organization = get_organization_by_id(organization_id)
            workspaces = get_user_workspaces_under_organization(organization_id)
            for workspace in workspaces:
                workspace.teams_count = get_workspace_teams_by_workspace_id(
                    workspace.workspace_id
                ).count()
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


def add_team_to_workspace(request, organization_id, workspace_id):
    organization = get_organization_by_id(organization_id)
    workspace = get_workspace_by_id(workspace_id)

    if request.method == "POST":
        form = AddTeamToWorkspaceForm(
            request.POST, organization=organization, workspace=workspace
        )
        try:
            if form.is_valid():
                WorkspaceTeam.objects.create(
                    workspace_id=workspace_id,
                    team_id=form.cleaned_data["team"].team_id,
                )
                workspaces = get_user_workspaces_under_organization(organization_id)
                for workspace in workspaces:
                    workspace.teams_count = get_workspace_teams_by_workspace_id(
                        workspace.workspace_id
                    ).count()
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
                response = HttpResponse(f"{message_html} {workspace_display_html}")
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
                response = HttpResponse(f"{message_html} {add_team_form_html}")
                return response
        except AddTeamToWorkspaceError as e:
            messages.error(request, str(e))
            return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
    else:
        form = AddTeamToWorkspaceForm(organization=organization)
        return render(request, "workspaces/partials/add_team_form.html", {"form": form})


def get_workspace_teams(request, organization_id, workspace_id):
    workspace = get_workspace_by_id(workspace_id)
    if request.headers.get("HX-Request"):
        workspace_teams = get_workspace_teams_by_workspace_id(workspace_id)
        print(workspace_teams)
        context = {
            "workspace_teams": workspace_teams,
            "workspace": workspace,
        }
        return render(request, "workspaces/workspace_teams.html", context) 
    return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")