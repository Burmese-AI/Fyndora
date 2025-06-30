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
from apps.teams.exceptions import TeamMemberCreationError


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
        if request.method == "POST":
            form = TeamForm(request.POST, organization=organization)
            if form.is_valid():
                create_team_from_form(form, organization=organization)
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
                    team_display_html = render_to_string(
                        "teams/partials/teams_display.html",
                        context=context,
                        request=request,
                    )
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    response = HttpResponse(f"{message_html} {team_display_html}")
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


def get_team_members_view(request, organization_id, team_id):
    try:
        # Get the team and organization for context
        team = get_team_by_id(team_id)
        organization = get_organization_by_id(organization_id)
        team_members = TeamMember.objects.filter(team=team)

        context = {
            "team": team,
            "organization": organization,
            "team_members": team_members,
        }
        return render(request, "teams/teamMembers_index.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/teams/")


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
                    team_members = TeamMember.objects.filter(team=team)
                    context = {
                        "team": team,
                        "organization": organization,
                        "team_members": team_members,
                        "is_oob": True,
                    }
                    team_display_html = render_to_string(
                        "teams/partials/teamMembers_display.html",
                        context=context,
                        request=request,
                    )
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    response = HttpResponse(f"{message_html} {team_display_html}")
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
                        "teams/partials/add_team_member_form.html",
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
            return render(request, "teams/partials/add_team_member_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect("teams", organization_id=organization_id)
