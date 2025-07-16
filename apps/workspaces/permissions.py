from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group
from apps.core.roles import get_permissions_for_role
from apps.core.permissions import OrganizationPermissions


def assign_workspace_permissions(workspace):
    """
    Assigns the necessary permissions to the group for the workspace.

    Args:
        workspace (Workspace): The workspace instance.
        group (Group): The Django group instance.
    """

    workspace_admins_group_name = f"Workspace Admins - {workspace.workspace_id}"
    operations_reviewer_group_name = f"Operations Reviewer - {workspace.workspace_id}"
    print(f"Workspace admins group name: {workspace_admins_group_name}")
    try:
        workspace_admins_group, _ = Group.objects.get_or_create(
            name=workspace_admins_group_name
        )
        operations_reviewer_group, _ = Group.objects.get_or_create(
            name=operations_reviewer_group_name
        )

        # getting the permissions for the workspace admin and operations reviewer

        workspace_admin_permissions = get_permissions_for_role("WORKSPACE_ADMIN")
        operations_reviewer_permissions = get_permissions_for_role(
            "OPERATIONS_REVIEWER"
        )

        for perm in workspace_admin_permissions:
            if perm == OrganizationPermissions.ADD_WORKSPACE:
                assign_perm(perm, workspace_admins_group, workspace.organization)
            else:
                assign_perm(perm, workspace_admins_group, workspace)

        for perm in operations_reviewer_permissions:
            assign_perm(perm, operations_reviewer_group, workspace)

        print(f"Assigned permissions to {workspace_admins_group} for {workspace}")
        print(f"Assigned permissions to {operations_reviewer_group} for {workspace}")

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
    """
    print("before")
    print(f"previous_admin: {previous_admin}")
    print(f"new_admin: {new_admin}")
    print(f"previous_operations_reviewer: {previous_operations_reviewer}")
    print(f"new_operations_reviewer: {new_operations_reviewer}")
    if (
        previous_admin == new_admin
        and previous_operations_reviewer == new_operations_reviewer
    ):
        return  # No change for workspace admin and operations reviewer
    print("after")
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
        print("workspace admin removed")
    if new_admin:
        workspace_admins_group.user_set.add(new_admin.user)
        print("new workspace admin added")

    if previous_operations_reviewer:
        operations_reviewer_group.user_set.remove(previous_operations_reviewer.user)
        print("operations reviewer removed")
    if new_operations_reviewer:
        operations_reviewer_group.user_set.add(new_operations_reviewer.user)
        print("new operations reviewer added")


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
