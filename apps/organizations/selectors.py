from apps.organizations.models import Organization


# get all organizations when user is a member
def get_user_organization(user):
    return Organization.objects.filter(
        members__user=user,
        members__is_active=True
    ).select_related('owner')