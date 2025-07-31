from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from guardian.shortcuts import assign_perm, get_user_perms, remove_perm

from apps.core.permissions import OrganizationPermissions, TeamPermissions
from apps.core.utils import permission_denied_view


def assign_team_permissions(team, coordinator=None):
    """
    Assign team permissions to a coordinator.

    Args:
        team: The team object
        coordinator: The coordinator to assign permissions to (optional)
    """
    if team is None:
        return

    # Use the expected group name format from tests
    team_coordinator_group_name = f"team_{team.team_id}_coordinators"

    team_coordinator_group, _ = Group.objects.get_or_create(
        name=team_coordinator_group_name
    )

    # Define the permissions to assign to the coordinator group
    permissions_to_assign = [
        "change_team",
        "delete_team",
        "add_teammember",
        "change_teammember",
        "delete_teammember",
    ]

    try:
        # Get the content type for the Team model
        team_content_type = ContentType.objects.get_for_model(team.__class__)
        teammember_content_type = ContentType.objects.get_for_model(team.members.model)

        # Assign permissions to the group
        for perm_codename in permissions_to_assign:
            try:
                if (
                    perm_codename.startswith("add_teammember")
                    or perm_codename.startswith("change_teammember")
                    or perm_codename.startswith("delete_teammember")
                ):
                    # TeamMember permissions
                    permission = Permission.objects.get(
                        codename=perm_codename, content_type=teammember_content_type
                    )
                else:
                    # Team permissions
                    permission = Permission.objects.get(
                        codename=perm_codename, content_type=team_content_type
                    )
                assign_perm(perm_codename, team_coordinator_group, team)
            except Permission.DoesNotExist:
                # If permission doesn't exist, skip it
                continue

        # Add coordinator to group if provided
        if coordinator is not None:
            team_coordinator_group.user_set.add(coordinator.user)

        # Also add organization owner if exists
        if (
            hasattr(team, "organization")
            and team.organization
            and team.organization.owner
        ):
            team_coordinator_group.user_set.add(team.organization.owner.user)

    except Exception as e:
        print(f"Error assigning team permissions: {e}")
        raise e


def remove_team_permissions(team):
    """
    Remove team permissions by deleting the coordinator group.

    Args:
        team: The team object
    """
    if team is None:
        return

    try:
        team_coordinator_group_name = f"team_{team.team_id}_coordinators"
        team_coordinator_group = Group.objects.filter(
            name=team_coordinator_group_name
        ).first()

        if team_coordinator_group:
            # Remove permissions before deleting group
            permissions_to_remove = [
                "change_team",
                "delete_team",
                "add_teammember",
                "change_teammember",
                "delete_teammember",
            ]

            for perm in permissions_to_remove:
                remove_perm(perm, team_coordinator_group, team)

            team_coordinator_group.delete()
    except Exception as e:
        print(f"Error removing team permissions: {e}")
        raise e


def update_team_coordinator_group(team, new_coordinator):
    """
    Update team coordinator group membership.

    Args:
        team: The team object
        new_coordinator: The new coordinator to assign (optional)
    """
    if team is None:
        return

    try:
        team_coordinator_group_name = f"team_{team.team_id}_coordinators"
        team_coordinator_group = Group.objects.filter(
            name=team_coordinator_group_name
        ).first()

        if team_coordinator_group:
            # Clear all users and add new coordinator
            team_coordinator_group.user_set.clear()

            if new_coordinator is not None:
                team_coordinator_group.user_set.add(new_coordinator.user)

    except Exception as e:
        print(f"Error updating team coordinator group: {e}")
        raise e


def check_add_team_permission(user, organization):
    """
    Check if user has permission to add teams to organization.

    Args:
        user: The user to check
        organization: The organization object

    Returns:
        bool: True if user has permission, False otherwise
    """
    if user is None or organization is None:
        return False

    user_perms = get_user_perms(user, organization)
    return "add_team" in user_perms


def check_change_team_permission(user, team):
    """
    Check if user has permission to change team.

    Args:
        user: The user to check
        team: The team object

    Returns:
        bool: True if user has permission, False otherwise
    """
    if user is None or team is None:
        return False

    user_perms = get_user_perms(user, team)
    return "change_team" in user_perms


def check_delete_team_permission(user, team):
    """
    Check if user has permission to delete team.

    Args:
        user: The user to check
        team: The team object

    Returns:
        bool: True if user has permission, False otherwise
    """
    if user is None or team is None:
        return False

    user_perms = get_user_perms(user, team)
    return "delete_team" in user_perms


def check_add_team_member_permission(user, team):
    """
    Check if user has permission to add team members.

    Args:
        user: The user to check
        team: The team object

    Returns:
        bool: True if user has permission, False otherwise
    """
    if user is None or team is None:
        return False

    user_perms = get_user_perms(user, team)
    return "add_teammember" in user_perms


def check_view_team_permission(user, team):
    """
    Check if user has permission to view team.

    Args:
        user: The user to check
        team: The team object

    Returns:
        bool: True if user has permission, False otherwise
    """
    if user is None or team is None:
        return False

    user_perms = get_user_perms(user, team)
    return "view_team" in user_perms


# Legacy functions for backward compatibility with views
def check_add_team_permission_view(request, organization):
    """Legacy function for view permission checking."""
    if not request.user.has_perm(OrganizationPermissions.ADD_TEAM, organization):
        return permission_denied_view(
            request,
            "You do not have permission to create a team in this organization.",
        )


def check_change_team_permission_view(request, team):
    """Legacy function for view permission checking."""
    if not request.user.has_perm(TeamPermissions.CHANGE_TEAM, team):
        return permission_denied_view(
            request,
            "You do not have permission to change the team in this organization.",
        )


def check_delete_team_permission_view(request, team):
    """Legacy function for view permission checking."""
    if not request.user.has_perm(TeamPermissions.DELETE_TEAM, team):
        return permission_denied_view(
            request,
            "You do not have permission to delete the team in this organization.",
        )


def check_add_team_member_permission_view(request, team):
    """Legacy function for view permission checking."""
    if not request.user.has_perm(TeamPermissions.ADD_TEAM_MEMBER, team):
        return permission_denied_view(
            request,
            "You do not have permission to add a team member to this team.",
        )


def check_view_team_permission_view(request, team):
    """Legacy function for view permission checking."""
    if not request.user.has_perm(TeamPermissions.VIEW_TEAM, team):
        return permission_denied_view(
            request,
            "You do not have permission to view the team in this organization.",
        )
