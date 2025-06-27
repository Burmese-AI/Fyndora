# apps/workspaces/selectors.py

from apps.workspaces.models import Workspace
from apps.organizations.models import Organization
from apps.organizations.models import OrganizationMember
from apps.teams.models import Team
from apps.workspaces.models import WorkspaceTeam


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
        return OrganizationMember.objects.filter(organization=organization_id)
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
