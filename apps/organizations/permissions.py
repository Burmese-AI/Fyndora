from apps.core.permissions import OrganizationPermissions


def can_manage_organization(user, organization):
    """
    Returns True if the user has the permission to manage the organization.
    """
    return user.has_perm(OrganizationPermissions.MANAGE_ORGANIZATION, organization)