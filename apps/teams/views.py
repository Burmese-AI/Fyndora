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


# Create your views here.
def teams_view(request, organization_id):
    try:
        teams = get_teams_by_organization_id(organization_id)
        attached_workspaces = []  # Initialize the variable
        for team in teams:
            attached_workspaces = WorkspaceTeam.objects.filter(team_id=team.team_id)
            team.attached_workspaces = attached_workspaces
        organization = get_organization_by_id(organization_id)
        context = {
            "teams": teams,
            "organization": organization,
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
        if request.method == "POST":
            form = TeamForm(request.POST, organization=organization)
            if form.is_valid():
                create_team_from_form(form, organization=organization, orgMember=orgMember)
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
                return HttpResponseClientRedirect(f"/{organization_id}/teams/")
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
        return HttpResponseClientRedirect(f"/{organization_id}/teams/")



def edit_team_view(request, organization_id, team_id):
    try:
        print("edit from view")
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)
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
                update_team_from_form(form, team=team, organization=organization)

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
        return HttpResponseClientRedirect(f"/{organization_id}/teams/")


def delete_team_view(request, organization_id, team_id):
    try:
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)
        workspace_teams = WorkspaceTeam.objects.filter(team_id=team_id)
        
        # Check if team exists
        if not team:
            messages.error(request, "Team not found.")
            return HttpResponseClientRedirect(f"/{organization_id}/teams/")
        
        # Check if team is attached to workspaces
        if workspace_teams.exists():
            messages.error(request, "Team is attached to workspaces. Please remove the team from all workspaces before deleting.")
            return HttpResponseClientRedirect(f"/{organization_id}/teams/")

        # Delete team and workspace teams
        if request.method == "POST":
            try:
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
                return HttpResponseClientRedirect(f"/{organization_id}/teams/")
        else:
            context = {
                "team": team,
                "organization": organization,
            }
            return render(request, "teams/partials/delete_team_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/teams/")


def get_team_members_view(request, organization_id, team_id):
    try:
        # Get the team and organization for context
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)
        team_members = get_team_members_by_team_id(team_id)

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
                return HttpResponseClientRedirect(
                    f"/{organization_id}/teams/team_members/{team_id}/"
                )
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
                return HttpResponseClientRedirect(
                    f"/{organization_id}/teams/team_members/{team_id}/"
                )
            except TeamMemberDeletionError as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return HttpResponseClientRedirect(
                    f"/{organization_id}/teams/team_members/{team_id}/"
                )
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
                return HttpResponseClientRedirect(
                    f"/{organization_id}/teams/team_members/{team_id}/"
                )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(
            f"/{organization_id}/teams/team_members/{team_id}/"
        )


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
        return HttpResponseClientRedirect(
            f"/{organization_id}/teams/team_members/{team_id}/"
        )
