from django.db import transaction
from apps.workspaces.models import Workspace
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.core.utils import model_update
from apps.workspaces.models import WorkspaceTeam
from django.contrib.auth.models import Group
from apps.workspaces.permissions import assign_workspace_permissions


@transaction.atomic
def create_workspace_from_form(*, form, orgMember, organization) -> Workspace:
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
        workspace.created_by = orgMember
        workspace.save()

        assign_workspace_permissions(workspace)
        return workspace
    except Exception as e:
        raise WorkspaceCreationError(f"Failed to create workspace: {str(e)}")


@transaction.atomic
def update_workspace_from_form(
    *, form, workspace, previous_workspace_admin
) -> Workspace:
    """
    Updates a workspace from a form.
    """
    try:
        workspace = model_update(workspace, form.cleaned_data)
        previous_workspace_admin = previous_workspace_admin
        new_workspace_admin = form.cleaned_data.get("workspace_admin")
        if previous_workspace_admin != new_workspace_admin:
            group_name = f"Workspace Admins - {workspace.workspace_id}"
            group, _ = Group.objects.get_or_create(name=group_name)

            # Add new workspace admin if not None
            if new_workspace_admin is not None:
                group.user_set.add(new_workspace_admin.user)

            # Remove previous workspace admin if not None
            if previous_workspace_admin is not None:
                group.user_set.remove(previous_workspace_admin.user)

        return workspace
    except Exception as e:
        raise WorkspaceUpdateError(f"Failed to update workspace: {str(e)}")


def remove_team_from_workspace(workspace_id, team_id):
    workspace_team = WorkspaceTeam.objects.get(
        workspace_id=workspace_id, team_id=team_id
    )
    workspace_team.delete()
    return workspace_team


def add_team_to_workspace(workspace_id, team_id):
    workspace_team = WorkspaceTeam.objects.create(
        workspace_id=workspace_id, team_id=team_id
    )
    return workspace_team
