from apps.organizations.models import Organization

def get_user_organizations(user):
    return Organization.objects.filter(
        members__user_id=user, members__is_active=True
    )