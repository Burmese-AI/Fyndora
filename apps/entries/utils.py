from apps.core.permissions import OrganizationPermissions

def can_view_org_expense(user, organization):
    """
    Returns True if the user has the permission to view the organization expense.
    """
    return user.has_perm(OrganizationPermissions.VIEW_ORG_ENTRY, organization)


def can_add_org_expense(user, organization):
    """
    Returns True if the user has the permission to add the organization expense.
    """
    return user.has_perm(OrganizationPermissions.ADD_ORG_ENTRY, organization)

def can_update_org_expense(user, organization):
    """
    Returns True if the user has the permission to update the organization expense.
    """
    return user.has_perm(OrganizationPermissions.CHANGE_ORG_ENTRY, organization)

def can_delete_org_expense(user, organization):
    """
    Returns True if the user has the permission to delete the organization expense.
    """
    return user.has_perm(OrganizationPermissions.DELETE_ORG_ENTRY, organization)
