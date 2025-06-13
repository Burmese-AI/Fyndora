# apps/workspaces/selectors.py

from apps.workspaces.models import Workspace
from apps.organizations.models import Organization


def get_user_workspaces_under_organization(organization_id):
    """
    Return workspaces where the user is a member of the organization.
    """
    try:
        return Workspace.objects.filter(organization_id=organization_id)
    except Exception as e:
        print(f"Error in get_user_workspaces: {str(e)}")
        return Workspace.objects.none()


def get_organization_by_id(organization_id):
    """
    Return an organization by its ID.
    """
    try:
        return Organization.objects.get(organization_id=organization_id)
    except Exception as e:
        print(f"Error in get_organization_by_id: {str(e)}")
        return None
