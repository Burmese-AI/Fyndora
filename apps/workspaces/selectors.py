# apps/workspaces/selectors.py

from apps.workspaces.models import Workspace


def get_user_workspaces(user):
    """
    Return workspaces where the user is a member of the organization.
    """
    try:
        user_org_ids = user.organization_memberships.values_list(
            "organization_id", flat=True
        )
        return Workspace.objects.filter(organization_id__in=user_org_ids)
    except Exception as e:
        print(f"Error in get_user_workspaces: {str(e)}")
        return Workspace.objects.none()
