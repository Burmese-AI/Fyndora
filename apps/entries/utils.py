from apps.core.permissions import OrganizationPermissions

def can_view_org_expense(user, organization):
    """
    Returns True if the user has the permission to view the organization expense.
    """
    return user.has_perm(OrganizationPermissions.VIEW_ORG_ENTRY, organization)