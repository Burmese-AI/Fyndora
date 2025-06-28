from apps.organizations.models import Organization


def get_organization_by_id(organization_id):
    """
    Return an organization by its ID.
    """
    try:
        return Organization.objects.get(organization_id=organization_id)
    except Exception as e:
        print(f"Error in get_organization_by_id: {str(e)}")
        return None
