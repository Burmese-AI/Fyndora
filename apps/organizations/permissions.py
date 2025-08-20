from apps.core.permissions import OrganizationPermissions


def can_remove_org_member(user, organization):
    """
    Check if the user can remove the organization member.
    """
    return user.has_perm(OrganizationPermissions.REMOVE_ORG_MEMBER, organization)
