from apps.core.permissions import OrganizationPermissions


def can_remove_org_member(user, organization):
    """
    Check if the user can remove the organization member.
    """
    # for edge case purpose in test cases
    if user is None:
        return False
    # for edge case purpose in test cases
    if organization is None:
        return False
    return user.has_perm(OrganizationPermissions.REMOVE_ORG_MEMBER, organization)
