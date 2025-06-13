from django.db import transaction
from apps.workspaces.models import Workspace
from apps.workspaces.exceptions import WorkspaceCreationError


@transaction.atomic
def create_workspace_from_form(*, form, organization) -> Workspace:
    """
    Creates a new workspace from a form and assigns it to an organization.

    Args:
        form: WorkspaceForm instance (already validated)
        organization: Organization instance the workspace belongs to

    Returns:
        Workspace: The created workspace instance
    """
    try:
        workspace = form.save(commit=False)
        workspace.organization = organization
        workspace.save()
        return workspace
    except Exception as e:
        raise WorkspaceCreationError(f"Failed to create workspace: {str(e)}")
