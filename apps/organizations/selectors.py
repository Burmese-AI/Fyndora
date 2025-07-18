from apps.organizations.models import Organization, OrganizationMember
from apps.workspaces.models import StatusChoices
from apps.teams.models import Team


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


def get_user_org_membership(user, organization, prefetch_user=False):
    """
    Returns the user's org member object based on the provided organization
    """
    queryset = OrganizationMember.objects.filter(user=user, organization=organization)
    if prefetch_user:
        queryset = queryset.select_related("user")
    return queryset.first()


def get_org_members(*, organization=None, workspace=None, prefetch_user=False):
    """
    Returns all members of the given organization.
    """
    queryset = OrganizationMember.objects.all()
    if organization:
        queryset = queryset.filter(organization=organization)
    if workspace:
        queryset = queryset.filter(administered_workspaces=workspace)
    if prefetch_user:
        queryset = queryset.select_related("user")
    return queryset


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