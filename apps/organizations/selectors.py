from django.core.exceptions import ValidationError

from apps.organizations.models import (
    Organization,
    OrganizationExchangeRate,
    OrganizationMember,
)
from apps.teams.models import Team


# get all organizations when user is a member
def get_user_organizations(user):
    """
    Returns all organizations where the user is an active member.
    """
    return Organization.objects.filter(
        members__user=user,
        members__is_active=True,
        members__deleted_at__isnull=True,
    ).select_related("owner")


def get_organization_by_id(organization_id):
    """
    Returns the organization by its ID.
    """
    try:
        return Organization.objects.get(organization_id=organization_id)
    except Organization.DoesNotExist:
        return None


def get_organization_members_count(organization):
    """
    Returns the count of active members in the given organization.
    """
    try:
        count = organization.members.filter(is_active=True).count()
        return int(count) if count is not None else 0
    except Exception:
        return 0

def get_organization_member_by_id(member_id):
    """
    Returns the organization member by its ID.
    """
    try:
        return OrganizationMember.objects.get(organization_member_id=member_id)
    except Exception:
        return None

def get_workspaces_count(organization):
    """
    Returns the count of workspaces in the given organization.
    """
    try:
        # Count all non-deleted workspaces regardless of status
        count = organization.workspaces.count()
        return int(count) if count is not None else 0
    except Exception:
        return 0


def get_teams_count(organization):
    """
    Returns the count of teams in the given organization through its workspaces.
    """
    try:
        # Get distinct teams through workspace_teams relationship
        count = (
            Team.objects.filter(workspace_teams__workspace__organization=organization)
            .distinct()
            .count()
        )
        return int(count) if count is not None else 0
    except Exception:
        return 0


def get_user_org_membership(user, organization, prefetch_user=False):
    """
    Returns the user's org member object based on the provided organization
    """
    queryset = OrganizationMember.objects.filter(
        user=user, organization=organization, is_active=True
    )
    if prefetch_user:
        queryset = queryset.select_related("user")
    return queryset.first()


def get_org_members(*, organization=None, workspace=None, prefetch_user=False):
    """
    Returns all members of the given organization.
    """
    if not organization and not workspace:
        raise ValueError("Either organization or workspace must be provided")

    queryset = OrganizationMember.objects.filter(is_active=True)
    if organization:
        queryset = queryset.filter(organization=organization)
    if workspace:
        queryset = queryset.filter(administered_workspaces=workspace)
    if prefetch_user:
        queryset = queryset.select_related("user")
    return queryset


def get_org_exchange_rates(*, organization: Organization):
    """
    Returns all exchange rates of the given organization.
    """
    queryset = OrganizationExchangeRate.objects.filter(organization=organization)
    return queryset


def get_orgMember_by_user_id_and_organization_id(user_id, organization_id):
    """
    Return an organization member by its user ID.
    """
    if not user_id or not organization_id:
        raise ValidationError("user_id and organization_id must be provided")
    try:
        return OrganizationMember.objects.get(
            user_id=user_id, organization_id=organization_id, is_active=True
        )
    except OrganizationMember.DoesNotExist:
        return None
