from django.db import transaction
from apps.workspaces.models import Workspace
from apps.workspaces.exceptions import WorkspaceCreationError
from apps.organizations.models import OrganizationMember


@transaction.atomic
def create_workspace_with_admin(*, form, user, organization) -> Workspace:
    """
    Creates a new workspace and sets up the admin.

    Args:
        form: WorkspaceForm instance
        user: User instance who will be the admin
        organization: Organization instance the workspace belongs to

    Returns:
        Workspace: The created workspace instance

    Raises:
        WorkspaceCreationError: If workspace creation fails
    """
    try:
        # Get the organization member for the request user
        org_member = OrganizationMember.objects.get(
            organization=organization, user=user, is_active=True
        )

        # Create the workspace
        workspace = form.save(commit=False)
        workspace.organization = organization
        workspace.created_by = org_member
        workspace.save()

        return workspace
    except Exception as e:
        raise WorkspaceCreationError(f"Failed to create workspace: {str(e)}")
