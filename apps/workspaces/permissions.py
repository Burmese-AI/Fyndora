from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group


def assign_workspace_permissions(workspace):
    """
    Assigns the necessary permissions to the group for the workspace.

    Args:
        workspace (Workspace): The workspace instance.
        group (Group): The Django group instance.
    """

    group_name = f"Workspace Admins - {workspace.workspace_id}"
    group, _ = Group.objects.get_or_create(name=group_name)
    assign_perm("change_workspace", group, workspace)
    assign_perm("delete_workspace", group, workspace)

    # if workspace admin is not None, add it to the group
    if workspace.workspace_admin is not None:
        group.user_set.add(workspace.workspace_admin.user)

    # Give permission to the organization owner
    group.user_set.add(workspace.organization.owner.user)


def update_workspace_admin_group(workspace, previous_admin, new_admin):
    """
    Updates the workspace admin group membership.

    Args:
        workspace (Workspace): The workspace instance.
        previous_admin (UserProfile or None): The previous admin.
        new_admin (UserProfile or None): The new admin.
    """
    if previous_admin == new_admin:
        return  # No change

    group_name = f"Workspace Admins - {workspace.workspace_id}"
    group, _ = Group.objects.get_or_create(name=group_name)

    if previous_admin:
        group.user_set.remove(previous_admin.user)
    if new_admin:
        group.user_set.add(new_admin.user)
