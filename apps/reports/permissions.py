from apps.core.permissions import OrganizationPermissions


def can_view_report_page(user, organization):
    if user.has_perm(OrganizationPermissions.VIEW_REPORT_PAGE, organization):
        return True
    return False
