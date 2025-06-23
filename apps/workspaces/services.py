from django.db import transaction
from apps.workspaces.models import Workspace
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.core.utils import model_update
from apps.workspaces.models import WorkspaceTeam
from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group


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

        group_name = (
            f"Workspace Admins - {workspace.workspace_id}"
        )
        group, _ = Group.objects.get_or_create(name=group_name)
        print("this is the group", group.name)

        assign_perm("change_workspace", group, workspace)
        assign_perm("delete_workspace", group, workspace)

        if workspace.workspace_admin is not None:
            group.user_set.add(workspace.workspace_admin.user)

        # give permission to the organization owner
        group.user_set.add(workspace.organization.owner.user)
        return workspace
    except Exception as e:
        raise WorkspaceCreationError(f"Failed to create workspace: {str(e)}")


@transaction.atomic
def update_workspace_from_form(*, form, workspace) -> Workspace:
    """
    Updates a workspace from a form.
    """
    try:
        workspace = model_update(workspace, form.cleaned_data)
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
