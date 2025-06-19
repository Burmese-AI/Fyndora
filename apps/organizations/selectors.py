from apps.organizations.models import Organization, OrganizationMember
from apps.workspaces.models import StatusChoices
from apps.teams.models import Team
from django.shortcuts import get_object_or_404


# get all organizations when user is a member
def get_user_organizations(user):
    """
    Returns all organizations where the user is an active member.
    """
    return Organization.objects.filter(
        members__user=user, members__is_active=True
    ).select_related("owner")


def get_organization_members_count(organization):
    """
    Returns the count of active members in the given organization.
    """
    try:
        count = organization.members.filter(is_active=True).count()
        return int(count) if count is not None else 0
    except Exception:
        return 0


def get_workspaces_count(organization):
    """
    Returns the count of workspaces in the given organization.
    """
    try:
        count = organization.workspaces.filter(status=StatusChoices.ACTIVE).count()
        return int(count) if count is not None else 0
    except Exception:
        return 0


def get_teams_count(organization):
    """
    Returns the count of teams in the given organization through its workspaces.
    """
    try:
        # Get all teams through workspace_teams relationship
        count = Team.objects.filter(
            workspace_teams__workspace__organization=organization
        ).count()
        return int(count) if count is not None else 0
    except Exception:
        return 0
    
def get_user_org_membership(user, organization):
    """
    Returns the user's org member object based on the provided organization
    """
    return OrganizationMember.objects.filter(user=user, organization=organization)
        