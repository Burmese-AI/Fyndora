from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group
from apps.core.roles import get_permissions_for_role
from apps.core.permissions import OrganizationPermissions
from apps.core.utils import permission_denied_view
from apps.core.permissions import WorkspacePermissions


def assign_workspace_permissions(workspace):
    """
    Assigns the necessary permissions to the group for the workspace.

    Args:
        workspace (Workspace): The workspace instance.
        group (Group): The Django group instance.
    """

    workspace_admins_group_name = f"Workspace Admins - {workspace.workspace_id}"
    operations_reviewer_group_name = f"Operations Reviewer - {workspace.workspace_id}"
    org_owner_group_name = f"Org Owner - {workspace.organization.organization_id}"

    try:
        workspace_admins_group, _ = Group.objects.get_or_create(
            name=workspace_admins_group_name
        )
        operations_reviewer_group, _ = Group.objects.get_or_create(
            name=operations_reviewer_group_name
        )
        org_owner_group, _ = Group.objects.get_or_create(name=org_owner_group_name)
        # getting the permissions for the workspace admin and operations reviewer

        workspace_admin_permissions = get_permissions_for_role("WORKSPACE_ADMIN")
        operations_reviewer_permissions = get_permissions_for_role(
            "OPERATIONS_REVIEWER"
        )
        org_owner_permissions = get_permissions_for_role("ORG_OWNER")

        for perm in workspace_admin_permissions:
            if (
                perm == OrganizationPermissions.ADD_TEAM
                or perm == OrganizationPermissions.MANAGE_ORGANIZATION
            ):
                assign_perm(perm, workspace_admins_group, workspace.organization)
            else:
                assign_perm(perm, workspace_admins_group, workspace)

        for perm in operations_reviewer_permissions:
            if perm == OrganizationPermissions.MANAGE_ORGANIZATION:
                assign_perm(perm, operations_reviewer_group, workspace.organization)
            else:
                assign_perm(perm, operations_reviewer_group, workspace)

        for perm in org_owner_permissions:
            if "workspace_currency" in perm:
                assign_perm(perm, org_owner_group, workspace)

        # adding owner and workspace admin to the workspace admin group
        if workspace.workspace_admin is not None:
            workspace_admins_group.user_set.add(workspace.workspace_admin.user)

        if workspace.organization.owner is not None:
            workspace_admins_group.user_set.add(workspace.organization.owner.user)

        # adding operations reviewer to the operations reviewer group
        if workspace.operations_reviewer is not None:
            operations_reviewer_group.user_set.add(workspace.operations_reviewer.user)

    except Exception as e:
        # You might want to log this error or handle it appropriately
        print(f"Error assigning workspace permissions: {e}")
        raise e


def update_workspace_admin_group(
    workspace,
    previous_admin,
    new_admin,
    previous_operations_reviewer,
    new_operations_reviewer,
):
    """
    Updates the workspace admin group membership.

    Args:
        workspace (Workspace): The workspace instance.
        previous_admin (UserProfile or None): The previous admin.
        new_admin (UserProfile or None): The new admin.
        previous_operations_reviewer (UserProfile or None): The previous operations reviewer.
        new_operations_reviewer (UserProfile or None): The new operations reviewer.
    """
    if (
        previous_admin == new_admin
        and previous_operations_reviewer == new_operations_reviewer
    ):
        return  # No change for workspace admin and operations reviewer
    workspace_admins_group_name = f"Workspace Admins - {workspace.workspace_id}"
    workspace_admins_group, _ = Group.objects.get_or_create(
        name=workspace_admins_group_name
    )

    operations_reviewer_group_name = f"Operations Reviewer - {workspace.workspace_id}"
    operations_reviewer_group, _ = Group.objects.get_or_create(
        name=operations_reviewer_group_name
    )

    if previous_admin:
        workspace_admins_group.user_set.remove(previous_admin.user)
    if new_admin:
        workspace_admins_group.user_set.add(new_admin.user)

    if previous_operations_reviewer:
        operations_reviewer_group.user_set.remove(previous_operations_reviewer.user)
    if new_operations_reviewer:
        operations_reviewer_group.user_set.add(new_operations_reviewer.user)


# check if the user has permission to create a workspace
def check_create_workspace_permission(request, organization):
    """
    Checks if the user is the organization owner. If not, returns an error response.
    """
    if not request.user.has_perm(OrganizationPermissions.ADD_WORKSPACE, organization):
        # that will route to the permission denied view
        return permission_denied_view(
            request,
            "You do not have permission to create a workspace in this organization.",
        )


# check if the user has permission to change the workspace admin
def check_change_workspace_admin_permission(request, organization):
    """
    Checks if the user is the organization owner. If not, returns an error response.
    """
    if not request.user.has_perm(
        OrganizationPermissions.CHANGE_WORKSPACE_ADMIN, organization
    ):
        return permission_denied_view(
            request,
            "You do not have permission to change the workspace admin in this organization.",
        )


# check if the user has permission to edit the workspace
def check_change_workspace_permission(request, workspace):
    if not request.user.has_perm(WorkspacePermissions.CHANGE_WORKSPACE, workspace):
        return permission_denied_view(
            request,
            "You do not have permission to change the workspace in this organization.",
        )



def assign_workspace_team_permissions(workspace_team):
    """
    Assigns the necessary permissions to the group for the workspace team.
    """
    workspace_team_group_name = f"Workspace Team - {workspace_team.workspace_team_id}"
    workspace_team_group, _ = Group.objects.get_or_create(name=workspace_team_group_name)

    workspace_team_permissions = get_permissions_for_role("SUBMITTER")
    for perm in workspace_team_permissions:
        assign_perm(perm, workspace_team_group, workspace_team)

    # adding the team members to the workspace team group
    for member in workspace_team.team.members.all():
        print(member)
        workspace_team_group.user_set.add(member.user)

   # adding owner to the workspace team group
    if workspace_team.workspace.organization.owner is not None:
        print("the owner is", workspace_team.workspace.organization.owner)
        workspace_team_group.user_set.add(workspace_team.workspace.organization.owner.user)

    return workspace_team_group