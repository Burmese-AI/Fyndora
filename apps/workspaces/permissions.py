from django.db import models
from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group


class WorkspacePermissions(models.TextChoices):
    """
    Permissions for the Workspace model.
    """
    ADD_WORKSPACE = "workspaces.add_workspace", "Can add workspace"
    CHANGE_WORKSPACE = "workspaces.change_workspace", "Can change workspace"
    DELETE_WORKSPACE = "workspaces.delete_workspace", "Can delete workspace"
    VIEW_WORKSPACE = "workspaces.view_workspace", "Can view workspace"
    ASSIGN_TEAMS = "workspaces.assign_teams", "Can assign teams to workspace"
    LOCK_WORKSPACE = "workspaces.lock_workspace", "Can lock workspace"
    VIEW_DASHBOARD = "workspaces.view_dashboard", "Can view dashboard reports"
    EXPORT_REPORT = "workspaces.export_report", "Can export reports"


def assign_workspace_permissions(workspace):
    """
    Assigns the necessary permissions to the group for the workspace.

    Args:
        workspace (Workspace): The workspace instance.
        group (Group): The Django group instance.
    """

    group_name = f"Workspace Admins - {workspace.workspace_id}"
    group, _ = Group.objects.get_or_create(name=group_name)
    assign_perm(WorkspacePermissions.CHANGE_WORKSPACE, group, workspace)
    assign_perm(WorkspacePermissions.DELETE_WORKSPACE, group, workspace)

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


# def check_org_owner_permission(request, org_member, organization_id):
#     """
#     Checks if the user is the organization owner. If not, returns an error response.

#     Args:
#         request: Django request object.
#         org_member: OrganizationMember instance.
#         organization_id: UUID or str of the organization.

#     Returns:
#         HttpResponse (rendered error page) if permission denied, otherwise None.
#     """
#     if not org_member.is_org_owner:
#         messages.error(request, "You do not have permission to do action in this organization.")
#         return HttpResponseClientRedirect(f"/403")
