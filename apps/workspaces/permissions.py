import logging

from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm

from apps.auditlog.business_logger import BusinessAuditLogger
from apps.core.permissions import OrganizationPermissions, WorkspacePermissions
from apps.core.roles import get_permissions_for_role
from apps.core.utils import permission_denied_view

logger = logging.getLogger(__name__)


def assign_workspace_permissions(workspace, request_user=None):
    """
    Assigns the necessary permissions to the group for the workspace.

    Args:
        workspace (Workspace): The workspace instance.
        request_user (User, optional): The user performing the operation for audit logging.
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

        # Track assigned permissions for audit logging
        assigned_permissions = []

        for perm in workspace_admin_permissions:
            if (
                perm == OrganizationPermissions.ADD_TEAM
                or perm == OrganizationPermissions.MANAGE_ORGANIZATION
            ):
                assign_perm(perm, workspace_admins_group, workspace.organization)
            else:
                assign_perm(perm, workspace_admins_group, workspace)
            assigned_permissions.append(f"WORKSPACE_ADMIN:{perm}")

        for perm in operations_reviewer_permissions:
            if perm == OrganizationPermissions.MANAGE_ORGANIZATION:
                assign_perm(perm, operations_reviewer_group, workspace.organization)
            else:
                assign_perm(perm, operations_reviewer_group, workspace)
            assigned_permissions.append(f"OPERATIONS_REVIEWER:{perm}")

        for perm in org_owner_permissions:
            if "workspace_currency" in perm:
                assign_perm(perm, org_owner_group, workspace)
                assigned_permissions.append(f"ORG_OWNER:{perm}")

        # Track user assignments for audit logging
        user_assignments = []

        # adding owner and workspace admin to the workspace admin group
        if workspace.workspace_admin is not None:
            workspace_admins_group.user_set.add(workspace.workspace_admin.user)
            user_assignments.append(
                f"workspace_admin:{workspace.workspace_admin.user.email}"
            )

        if workspace.organization.owner is not None:
            workspace_admins_group.user_set.add(workspace.organization.owner.user)
            user_assignments.append(
                f"org_owner:{workspace.organization.owner.user.email}"
            )

        # adding operations reviewer to the operations reviewer group
        if workspace.operations_reviewer is not None:
            operations_reviewer_group.user_set.add(workspace.operations_reviewer.user)
            user_assignments.append(
                f"operations_reviewer:{workspace.operations_reviewer.user.email}"
            )

        # Log permission assignment for audit trail
        if request_user:
            try:
                BusinessAuditLogger.log_permission_change(
                    user=request_user,
                    target_user=workspace.workspace_admin
                    or workspace.organization.owner,
                    permission="workspace_permissions_setup",
                    action="grant",
                    reason="Workspace permission initialization",
                    workspace_id=str(workspace.workspace_id),
                    workspace_title=workspace.title,
                    organization_id=str(workspace.organization.organization_id),
                    organization_title=workspace.organization.title,
                    assigned_permissions=assigned_permissions,
                    user_assignments=user_assignments,
                    groups_created=[
                        workspace_admins_group_name,
                        operations_reviewer_group_name,
                        org_owner_group_name,
                    ],
                )
            except Exception as log_error:
                logger.error(
                    f"Failed to log workspace permission assignment: {log_error}",
                    exc_info=True,
                )

    except Exception as e:
        logger.error(f"Error assigning workspace permissions: {e}", exc_info=True)
        raise e


def update_workspace_admin_group(
    workspace,
    previous_admin,
    new_admin,
    previous_operations_reviewer,
    new_operations_reviewer,
    request_user=None,
):
    """
    Updates the workspace admin group membership.

    Args:
        workspace (Workspace): The workspace instance.
        previous_admin (UserProfile or None): The previous admin.
        new_admin (UserProfile or None): The new admin.
        previous_operations_reviewer (UserProfile or None): The previous operations reviewer.
        new_operations_reviewer (UserProfile or None): The new operations reviewer.
        request_user (User, optional): The user performing the operation for audit logging.
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

    # Track changes for audit logging
    admin_changes = []
    reviewer_changes = []

    if previous_admin:
        workspace_admins_group.user_set.remove(previous_admin.user)
        admin_changes.append(f"removed:{previous_admin.user.email}")
    if new_admin:
        workspace_admins_group.user_set.add(new_admin.user)
        admin_changes.append(f"added:{new_admin.user.email}")

    if previous_operations_reviewer:
        operations_reviewer_group.user_set.remove(previous_operations_reviewer.user)
        reviewer_changes.append(f"removed:{previous_operations_reviewer.user.email}")
    if new_operations_reviewer:
        operations_reviewer_group.user_set.add(new_operations_reviewer.user)
        reviewer_changes.append(f"added:{new_operations_reviewer.user.email}")

    # Log admin role changes
    if admin_changes and request_user:
        try:
            target_user = new_admin or previous_admin
            if target_user:
                BusinessAuditLogger.log_permission_change(
                    user=request_user,
                    target_user=target_user,
                    permission="workspace_admin_role",
                    action="grant" if new_admin else "revoke",
                    reason="Workspace admin role change",
                    workspace_id=str(workspace.workspace_id),
                    workspace_title=workspace.title,
                    organization_id=str(workspace.organization.organization_id),
                    organization_title=workspace.organization.title,
                    role_changes=admin_changes,
                    previous_admin_email=previous_admin.user.email
                    if previous_admin
                    else None,
                    new_admin_email=new_admin.user.email if new_admin else None,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace admin change: {log_error}", exc_info=True
            )

    # Log reviewer role changes
    if reviewer_changes and request_user:
        try:
            target_user = new_operations_reviewer or previous_operations_reviewer
            if target_user:
                BusinessAuditLogger.log_permission_change(
                    user=request_user,
                    target_user=target_user,
                    permission="operations_reviewer_role",
                    action="grant" if new_operations_reviewer else "revoke",
                    reason="Operations reviewer role change",
                    workspace_id=str(workspace.workspace_id),
                    workspace_title=workspace.title,
                    organization_id=str(workspace.organization.organization_id),
                    organization_title=workspace.organization.title,
                    role_changes=reviewer_changes,
                    previous_reviewer_email=previous_operations_reviewer.user.email
                    if previous_operations_reviewer
                    else None,
                    new_reviewer_email=new_operations_reviewer.user.email
                    if new_operations_reviewer
                    else None,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log operations reviewer change: {log_error}", exc_info=True
            )


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


def assign_workspace_team_permissions(workspace_team, request_user=None):
    """
    Assigns the necessary permissions to the group for the workspace team.
    """
    workspace_team_group_name = f"Workspace Team - {workspace_team.workspace_team_id}"
    workspace_team_group, _ = Group.objects.get_or_create(
        name=workspace_team_group_name
    )

    workspace_team_permissions = get_permissions_for_role("SUBMITTER")
    assigned_permissions = []

    for perm in workspace_team_permissions:
        assign_perm(perm, workspace_team_group, workspace_team)
        assigned_permissions.append(f"SUBMITTER:{perm}")

    # Track user assignments for audit logging
    user_assignments = []

    # adding the team members to the workspace team group
    for member in workspace_team.team.members.all():
        workspace_team_group.user_set.add(member.organization_member.user)
        user_assignments.append(f"team_member:{member.organization_member.user.email}")

    # adding owner to the workspace team group
    if workspace_team.workspace.organization.owner is not None:
        workspace_team_group.user_set.add(
            workspace_team.workspace.organization.owner.user
        )
        user_assignments.append(
            f"org_owner:{workspace_team.workspace.organization.owner.user.email}"
        )

    # Log workspace team permission assignment
    if request_user:
        try:
            # Use the first team member as target user, or org owner as fallback
            target_user = None
            if workspace_team.team.members.exists():
                target_user = workspace_team.team.members.first().organization_member
            elif workspace_team.workspace.organization.owner:
                target_user = workspace_team.workspace.organization.owner

            if target_user:
                BusinessAuditLogger.log_permission_change(
                    user=request_user,
                    target_user=target_user,
                    permission="workspace_team_permissions",
                    action="grant",
                    reason="Workspace team permission assignment",
                    workspace_id=str(workspace_team.workspace.workspace_id),
                    workspace_title=workspace_team.workspace.title,
                    team_id=str(workspace_team.team.team_id),
                    team_name=workspace_team.team.name,
                    workspace_team_id=str(workspace_team.workspace_team_id),
                    organization_id=str(
                        workspace_team.workspace.organization.organization_id
                    ),
                    organization_title=workspace_team.workspace.organization.title,
                    assigned_permissions=assigned_permissions,
                    user_assignments=user_assignments,
                    group_created=workspace_team_group_name,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace team permission assignment: {log_error}",
                exc_info=True,
            )

    return workspace_team_group


def remove_workspace_team_permissions(workspace_team, request_user=None):
    """
    Removes the necessary permissions from the group for the workspace team.
    """
    try:
        workspace_team_group_name = (
            f"Workspace Team - {workspace_team.workspace_team_id}"
        )
        workspace_team_group = Group.objects.filter(
            name=workspace_team_group_name
        ).first()

        if workspace_team_group is not None:
            # Collect information for audit logging before deletion
            removed_users = []
            if workspace_team_group.user_set.exists():
                removed_users = [
                    user.email for user in workspace_team_group.user_set.all()
                ]

            workspace_team_group.delete()

            # Log workspace team permission removal
            if request_user:
                try:
                    # Use the first team member as target user, or org owner as fallback
                    target_user = None
                    if workspace_team.team.members.exists():
                        target_user = (
                            workspace_team.team.members.first().organization_member
                        )
                    elif workspace_team.workspace.organization.owner:
                        target_user = workspace_team.workspace.organization.owner

                    if target_user:
                        BusinessAuditLogger.log_permission_change(
                            user=request_user,
                            target_user=target_user,
                            permission="workspace_team_permissions",
                            action="revoke",
                            reason="Workspace team permission removal",
                            workspace_id=str(workspace_team.workspace.workspace_id),
                            workspace_title=workspace_team.workspace.title,
                            team_id=str(workspace_team.team.team_id),
                            team_name=workspace_team.team.name,
                            workspace_team_id=str(workspace_team.workspace_team_id),
                            organization_id=str(
                                workspace_team.workspace.organization.organization_id
                            ),
                            organization_title=workspace_team.workspace.organization.title,
                            removed_users=removed_users,
                            group_deleted=workspace_team_group_name,
                        )
                except Exception as log_error:
                    logger.error(
                        f"Failed to log workspace team permission removal: {log_error}",
                        exc_info=True,
                    )
        else:
            logger.debug(
                f"Workspace team group '{workspace_team_group_name}' not found - may have been already deleted"
            )

    except Exception as e:
        logger.error(
            f"Error in remove_workspace_team_permissions: {str(e)}", exc_info=True
        )
