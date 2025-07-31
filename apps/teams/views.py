from django.shortcuts import render
from apps.core.services.organizations import get_organization_by_id
from django.shortcuts import redirect
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect
from apps.workspaces.models import WorkspaceTeam
from apps.teams.forms import TeamForm
from apps.teams.selectors import get_teams_by_organization_id, get_team_by_id
from apps.teams.services import create_team_from_form
from django.template.loader import render_to_string
from django.http import HttpResponse
from apps.teams.models import TeamMember
from apps.teams.forms import TeamMemberForm
from apps.teams.services import create_team_member_from_form
from apps.teams.exceptions import TeamMemberCreationError, TeamMemberDeletionError
from apps.teams.selectors import get_team_member_by_id
from apps.teams.forms import EditTeamMemberRoleForm
from apps.teams.services import update_team_member_role
from apps.teams.selectors import get_team_members_by_team_id
from apps.organizations.selectors import get_orgMember_by_user_id_and_organization_id
from apps.teams.services import update_team_from_form, remove_team_member
from apps.core.permissions import OrganizationPermissions
from apps.teams.permissions import (
    check_add_team_permission_view,
    check_change_team_permission_view,
    check_delete_team_permission_view,
    check_add_team_member_permission_view,
    check_view_team_permission_view,
    remove_team_permissions,
)
from apps.core.utils import can_manage_organization, permission_denied_view
from django.contrib.auth.decorators import login_required


# Create your views here.
@login_required
def teams_view(request, organization_id):
    try:
        organization = get_organization_by_id(organization_id)
        if not can_manage_organization(request.user, organization):
            return permission_denied_view(
                request,
                "You do not have permission to access this organization.",
            )
        teams = get_teams_by_organization_id(organization_id)
        attached_workspaces = []  # Initialize the variable
        # to display the workspaces attached to the team
        for team in teams:
            attached_workspaces = WorkspaceTeam.objects.filter(team_id=team.team_id)
            team.attached_workspaces = attached_workspaces
        organization = get_organization_by_id(organization_id)
        # sending true or false to the template to display the new team button
        can_add_team = request.user.has_perm(
            OrganizationPermissions.ADD_TEAM, organization
        )  # false
        permissions = {
            "can_add_team": can_add_team,  # false
        }
        context = {
            "teams": teams,
            "organization": organization,
            "permissions": permissions,
        }
        return render(request, "teams/index.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect("teams", organization_id=organization_id)


def create_team_view(request, organization_id):
    try:
        organization = get_organization_by_id(organization_id)
        orgMember = get_orgMember_by_user_id_and_organization_id(
            request.user.user_id, organization_id
        )
        permission_check = check_add_team_permission_view(request, organization)
        if permission_check:
            return permission_check

        if request.method == "POST":
            form = TeamForm(request.POST, organization=organization)
            if form.is_valid():
                create_team_from_form(
                    form, organization=organization, orgMember=orgMember
                )
                messages.success(request, "Team created successfully.")
                if request.headers.get("HX-Request"):
                    teams = get_teams_by_organization_id(organization_id)
                    attached_workspaces = []  # Initialize the variable
                    for team in teams:
                        attached_workspaces = WorkspaceTeam.objects.filter(
                            team_id=team.team_id
                        )
                        team.attached_workspaces = attached_workspaces
                    context = {
                        "teams": teams,
                        "organization": organization,
                        "is_oob": True,
                    }
                    teams_grid_html = render_to_string(
                        "teams/partials/teams_grid.html",
                        context=context,
                        request=request,
                    )
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    response = HttpResponse(f"{message_html} {teams_grid_html}")
                    response["HX-trigger"] = "success"
                    return response
                if request.htmx:
                    return HttpResponseClientRedirect(f"/{organization_id}/teams/")
                else:
                    return redirect("teams", organization_id=organization_id)
            else:
                messages.error(request, "Invalid form data.")
                context = {"form": form, "is_oob": True}
                message_html = render_to_string(
                    "includes/message.html", context=context, request=request
                )
                modal_html = render_to_string(
                    "teams/partials/create_team_form.html",
                    context=context,
                    request=request,
                )
                return HttpResponse(f"{message_html} {modal_html}")
        else:
            form = TeamForm(organization=organization)
            context = {
                "form": form,
                "organization": organization,
            }
            return render(request, "teams/partials/create_team_form.html", context)
    except Exception as e:
        print(e)
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        if request.htmx:
            return HttpResponseClientRedirect(f"/{organization_id}/teams/")
        else:
            return redirect("teams", organization_id=organization_id)


def edit_team_view(request, organization_id, team_id):
    try:
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)
        previous_team_coordinator = team.team_coordinator

        permission_check = check_change_team_permission_view(request, team)
        if permission_check:
            return permission_check

        if request.method != "POST":
            form = TeamForm(instance=team, organization=organization)
            context = {
                "form": form,
                "organization": organization,
            }
            return render(request, "teams/partials/edit_team_form.html", context)
        else:
            form = TeamForm(request.POST, instance=team, organization=organization)
            if form.is_valid():
                update_team_from_form(
                    form,
                    team=team,
                    organization=organization,
                    previous_team_coordinator=previous_team_coordinator,
                )

                messages.success(request, "Team updated successfully.")
                teams = get_teams_by_organization_id(organization_id)
                attached_workspaces = []  # Initialize the variable
                for team in teams:
                    attached_workspaces = WorkspaceTeam.objects.filter(
                        team_id=team.team_id
                    )
                    team.attached_workspaces = attached_workspaces
                    context = {
                        "teams": teams,
                        "organization": organization,
                        "is_oob": True,
                    }
                    teams_grid_html = render_to_string(
                        "teams/partials/teams_grid.html",
                        context=context,
                        request=request,
                    )
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    response = HttpResponse(f"{message_html} {teams_grid_html}")
                    response["HX-trigger"] = "success"
                    return response
            else:
                messages.error(request, "Invalid form data.")
                context = {
                    "form": form,
                    "organization": organization,
                    "is_oob": True,
                }
                message_html = render_to_string(
                    "includes/message.html", context=context, request=request
                )
                modal_html = render_to_string(
                    "teams/partials/edit_team_form.html",
                    context=context,
                    request=request,
                )
                return HttpResponse(f"{message_html} {modal_html}")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        if request.htmx:
            return HttpResponseClientRedirect(f"/{organization_id}/teams/")
        else:
            return redirect("teams", organization_id=organization_id)


def delete_team_view(request, organization_id, team_id):
    try:
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)
        workspace_teams = WorkspaceTeam.objects.filter(team_id=team_id)

        permission_check = check_delete_team_permission_view(request, team)
        if permission_check:
            return permission_check

        # Check if team exists
        if not team:
            messages.error(request, "Team not found.")
            if request.htmx:
                return HttpResponseClientRedirect(f"/{organization_id}/teams/")
            else:
                return redirect("teams", organization_id=organization_id)

        # Note: WorkspaceTeam objects will be deleted along with the team due to CASCADE relationship

        # Delete team and workspace teams
        if request.method == "POST":
            try:
                remove_team_permissions(team)
                workspace_teams.delete()
                team.delete()
                messages.success(request, "Team deleted successfully.")
                teams = get_teams_by_organization_id(organization_id)
                attached_workspaces = []  # Initialize the variable
                for team in teams:
                    attached_workspaces = WorkspaceTeam.objects.filter(
                        team_id=team.team_id
                    )
                    team.attached_workspaces = attached_workspaces
                context = {
                    "teams": teams,
                    "organization": organization,
                    "is_oob": True,
                }
                teams_grid_html = render_to_string(
                    "teams/partials/teams_grid.html",
                    context=context,
                    request=request,
                )
                message_html = render_to_string(
                    "includes/message.html", context=context, request=request
                )
                response = HttpResponse(f"{message_html} {teams_grid_html}")
                response["HX-trigger"] = "success"
                return response
            except Exception as e:
                messages.error(request, f"Failed to delete team: {str(e)}")
                if request.htmx:
                    return HttpResponseClientRedirect(f"/{organization_id}/teams/")
                else:
                    return redirect("teams", organization_id=organization_id)
        else:
            context = {
                "team": team,
                "organization": organization,
            }
            return render(request, "teams/partials/delete_team_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        if request.htmx:
            return HttpResponseClientRedirect(f"/{organization_id}/teams/")
        else:
            return redirect("teams", organization_id=organization_id)


def get_team_members_view(request, organization_id, team_id):
    try:
        # Get the team and organization for context
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)
        team_members = get_team_members_by_team_id(team_id)

        permission_check = check_view_team_permission_view(request, team)
        if permission_check:
            return permission_check

        context = {
            "team": team,
            "organization": organization,
            "team_members": team_members,
        }
        return render(request, "team_members/index.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect("teams", organization_id=organization_id)


def add_team_member_view(request, organization_id, team_id):
    try:
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)

        permission_check = check_add_team_member_permission_view(request, team)
        if permission_check:
            return permission_check

        if request.method == "POST":
            try:
                form = TeamMemberForm(
                    request.POST, team=team, organization=organization
                )
                if form.is_valid():
                    create_team_member_from_form(
                        form, team=team, organization=organization
                    )
                    messages.success(request, "Team member added successfully.")
                    team_members = get_team_members_by_team_id(team_id)
                    context = {
                        "team": team,
                        "organization": organization,
                        "team_members": team_members,
                        "is_oob": True,
                    }
                    team_members_table_html = render_to_string(
                        "team_members/partials/team_members_table.html",
                        context=context,
                        request=request,
                    )
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    response = HttpResponse(f"{message_html} {team_members_table_html}")
                    response["HX-trigger"] = "success"
                    return response
                else:
                    messages.error(request, "Invalid form data.")
                    context = {
                        "form": form,
                        "team": team,
                        "organization": organization,
                        "is_oob": True,
                    }

                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    modal_html = render_to_string(
                        "team_members/partials/add_team_member_form.html",
                        context=context,
                        request=request,
                    )
                    return HttpResponse(f"{message_html} {modal_html}")
            except TeamMemberCreationError as e:
                messages.error(request, f"An error occurred: {str(e)}")
                if request.htmx:
                    return HttpResponseClientRedirect(
                        f"/{organization_id}/teams/team_members/{team_id}/"
                    )
                else:
                    return redirect("team_members", organization_id=organization_id, team_id=team_id)
        else:
            form = TeamMemberForm(team=team, organization=organization)
            context = {
                "form": form,
                "team": team,
                "organization": organization,
            }
            return render(
                request, "team_members/partials/add_team_member_form.html", context
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect("teams", organization_id=organization_id)


def remove_team_member_view(request, organization_id, team_id, team_member_id):
    try:
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)

        if request.method == "POST":
            try:
                team_member = get_team_member_by_id(team_member_id)
                remove_team_member(team_member)
                messages.success(request, "Team member removed successfully.")

                # Get updated team members list
                team_members = TeamMember.objects.filter(team=team)
                context = {
                    "team": team,
                    "organization": organization,
                    "team_members": team_members,
                    "is_oob": True,
                }

                team_members_table_html = render_to_string(
                    "team_members/partials/team_members_table.html",
                    context=context,
                    request=request,
                )
                message_html = render_to_string(
                    "includes/message.html", context=context, request=request
                )
                response = HttpResponse(f"{message_html} {team_members_table_html}")
                response["HX-trigger"] = "success"
                return response

            except TeamMember.DoesNotExist:
                messages.error(request, "Team member not found.")
                if request.htmx:
                    return HttpResponseClientRedirect(
                        f"/{organization_id}/teams/team_members/{team_id}/"
                    )
                else:
                    return redirect("team_members", organization_id=organization_id, team_id=team_id)
            except TeamMemberDeletionError as e:
                messages.error(request, f"An error occurred: {str(e)}")
                if request.htmx:
                    return HttpResponseClientRedirect(
                        f"/{organization_id}/teams/team_members/{team_id}/"
                    )
                else:
                    return redirect("team_members", organization_id=organization_id, team_id=team_id)
        else:
            try:
                team_member = TeamMember.objects.get(
                    team_member_id=team_member_id, team=team
                )
                context = {
                    "team_member": team_member,
                    "team": team,
                    "organization": organization,
                }
                return render(
                    request,
                    "team_members/partials/remove_team_member_form.html",
                    context,
                )
            except TeamMember.DoesNotExist:
                messages.error(request, "Team member not found.")
                if request.htmx:
                    return HttpResponseClientRedirect(
                        f"/{organization_id}/teams/team_members/{team_id}/"
                    )
                else:
                    return redirect("team_members", organization_id=organization_id, team_id=team_id)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        if request.htmx:
            return HttpResponseClientRedirect(
                f"/{organization_id}/teams/team_members/{team_id}/"
            )
        else:
            return redirect("team_members", organization_id=organization_id, team_id=team_id)


def edit_team_member_role_view(request, organization_id, team_id, team_member_id):
    try:
        team_member = get_team_member_by_id(team_member_id)
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)

        if request.method == "POST":
            print("post action")
            form = EditTeamMemberRoleForm(request.POST, instance=team_member)
            if form.is_valid():
                update_team_member_role(form=form, team_member=team_member)
                messages.success(request, "Team member role updated successfully.")

                # Get the updated team member
                team_members = get_team_members_by_team_id(team_id)
                context = {
                    "team": team,
                    "organization": organization,
                    "team_members": team_members,
                    "is_oob": True,
                }
                team_members_table_html = render_to_string(
                    "team_members/partials/team_members_table.html",
                    context=context,
                    request=request,
                )
                message_html = render_to_string(
                    "includes/message.html", context=context, request=request
                )
                response = HttpResponse(f"{message_html} {team_members_table_html}")
                response["HX-trigger"] = "success"
                return response
                # return HttpResponseClientRedirect(
                #     f"/{organization_id}/teams/team_members/{team_id}/"
                # )
            else:
                messages.error(request, "Invalid form data.")
                context = {
                    "form": form,
                    "team_member": team_member,
                    "team": team,
                    "organization": organization,
                    "is_oob": True,
                }
                modal_html = render_to_string(
                    "team_members/partials/edit_team_member_role_form.html",
                    context=context,
                    request=request,
                )
                message_html = render_to_string(
                    "includes/message.html", context=context, request=request
                )
                return HttpResponse(f"{message_html} {modal_html}")
        else:
            form = EditTeamMemberRoleForm(instance=team_member)
            context = {
                "form": form,
                "team_member": team_member,
                "team": team,
                "organization": organization,
            }
            return render(
                request,
                "team_members/partials/edit_team_member_role_form.html",
                context,
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        if request.htmx:
            return HttpResponseClientRedirect(
                f"/{organization_id}/teams/team_members/{team_id}/"
            )
        else:
            return redirect("team_members", organization_id=organization_id, team_id=team_id)
