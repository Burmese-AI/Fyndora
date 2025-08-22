from apps.core.permissions import OrganizationPermissions


def can_confirm_remittance_payment(user, organization):
    return user.has_perm(OrganizationPermissions.CONFIRM_REMITTANCE_PAYMENT, organization)






