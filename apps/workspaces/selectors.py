# apps/workspaces/selectors.py

from django.db.models import Q
from apps.workspaces.models import Workspace
from apps.organizations.models import Organization
from apps.organizations.models import OrganizationMember
from apps.teams.models import Team, TeamMember
from apps.workspaces.models import WorkspaceTeam


def get_workspace_team_member_by_workspace_team_and_org_member(
    workspace_team, org_member
):
    """
    Return the workspace team member by the workspace team and organization member.
    """
    return TeamMember.objects.filter(
        organization_member=org_member, team=workspace_team.team
    ).first()


def get_workspace_team_role_by_workspace_team_and_org_member(
    workspace_team, org_member
):
    """
    Return the role of the organization member in the workspace team.
    """
    return TeamMember.objects.get(
        organization_member=org_member, team=workspace_team.team
    ).role


def get_user_workspace_teams_under_organization(organization_id, user):
    """
    Return workspace teams where the user is a member of the organization.
    """

    # Get Workspaces where user is a member or a team coordinator of the team
    return (
        WorkspaceTeam.objects.filter(workspace__organization__pk=organization_id)
        .filter(
            Q(team__team_coordinator__user=user)
            | Q(team__members__organization_member__user=user)
        )
        .prefetch_related("workspace", "team")
    )


def get_all_related_workspace_teams(organization, user, group_by_workspace=True):
    """
    Returns either:
    - A dict of workspace -> list of workspace teams (default behavior)
    - Or a flat queryset, if group_by_workspace is False

    Includes:
    - All teams if user is organization owner
    - Otherwise, filters teams the user is directly involved in
    """
    is_owner = organization.owner and organization.owner.user == user
    print(f"is_owner => {is_owner}")
    qs = (
        WorkspaceTeam.objects.filter(workspace__organization=organization)
        .select_related("workspace")
        .prefetch_related("team")
    )

    if not is_owner:
        qs = qs.filter(
            Q(workspace__workspace_admin__user=user)
            | Q(workspace__operations_reviewer__user=user)
            | Q(team__team_coordinator__user=user)
            | Q(team__members__organization_member__user=user)
        ).distinct()

    if not group_by_workspace:
        return qs

    grouped = {}
    for workspace_team in qs:
        workspace = workspace_team.workspace
        if workspace not in grouped:
            grouped[workspace] = []
        grouped[workspace].append(workspace_team)

    return grouped


def get_user_workspaces_under_organization(organization_id):
    """
    Return workspaces where the user is a member of the organization.
    """
    try:
        return Workspace.objects.filter(organization_id=organization_id)
    except Exception as e:
        print(f"Error in get_user_workspaces: {str(e)}")
        return Workspace.objects.none()


def get_organization_by_id(organization_id):
    """
    Return an organization by its ID.
    """
    try:
        return Organization.objects.get(organization_id=organization_id)
    except Exception as e:
        print(f"Error in get_organization_by_id: {str(e)}")
        return None


def get_organization_members_by_organization_id(organization_id):
    """
    Return organization members by organization ID.
    """
    try:
        return OrganizationMember.objects.filter(organization_id=organization_id)
    except Exception as e:
        print(f"Error in get_organization_members_by_organization_id: {str(e)}")
        return None


def get_workspace_by_id(workspace_id):
    """
    Return a workspace by its ID.
    """
    try:
        return Workspace.objects.get(workspace_id=workspace_id)
    except Exception as e:
        print(f"Error in get_workspace_by_id: {str(e)}")
        return None


def get_orgMember_by_user_id_and_organization_id(user_id, organization_id):
    """
    Return an organization member by its user ID.
    """
    try:
        return OrganizationMember.objects.get(
            user_id=user_id, organization_id=organization_id
        )
    except Exception as e:
        print(f"Error in get_organization_member_by_user_id: {str(e)}")
        return None


def get_teams_by_organization_id(organization_id):
    """
    Return teams by organization ID.
    """
    try:
        return Team.objects.filter(organization_id=organization_id)
    except Exception as e:
        print(f"Error in get_teams_by_organization_id: {str(e)}")
        return None


def get_workspace_teams_by_workspace_id(workspace_id):
    """
    Return workspace teams by workspace ID.
    """
    try:
        return WorkspaceTeam.objects.filter(workspace_id=workspace_id).select_related(
            "team", "workspace"
        )
    except Exception as e:
        print(f"Error in get_workspace_teams_by_workspace_id: {str(e)}")
        return None


def get_team_by_id(team_id):
    """
    Return a team by its ID.
    """
    try:
        return Team.objects.get(team_id=team_id)
    except Exception as e:
        print(f"Error in get_team_by_id: {str(e)}")
        return None


def get_workspaces_with_team_counts(organization_id):
    workspaces = get_user_workspaces_under_organization(organization_id)
    for workspace in workspaces:
        workspace.teams_count = get_workspace_teams_by_workspace_id(
            workspace.workspace_id
        ).count()
    return workspaces


def get_single_workspace_with_team_counts(workspace_id):
    workspace = get_workspace_by_id(workspace_id)
    workspace.teams_count = get_workspace_teams_by_workspace_id(
        workspace.workspace_id
    ).count()
    return workspace


def get_workspace_team_by_workspace_team_id(workspace_team_id):
    """
    Return a workspace team by its ID.
    """
    try:
        return WorkspaceTeam.objects.get(workspace_team_id=workspace_team_id)
    except Exception as e:
        print(f"Error in get_workspace_team_by_id: {str(e)}")
        return None
