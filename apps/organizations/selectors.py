from apps.organizations.models import Organization


# get all organizations when user is a member
def get_user_organizations(user):
    """
    Returns all organizations where the user is an active member.
    """
    return Organization.objects.filter(
        members__user=user,
        members__is_active=True
    ).select_related('owner')


def get_organization_members_count(organization):
    """
    Returns the count of active members in the given organization.
    """
    return organization.members.filter(is_active=True).count()
