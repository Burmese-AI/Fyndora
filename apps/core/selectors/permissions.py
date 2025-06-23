from apps.core.permissions import Permissions
from apps.core.services.permissions import _role_has_permission
from apps.teams.models import TeamMember


def get_user_permissions(*, user, workspace=None, team=None):
    """
    Get all permissions a user has in a specific workspace or team context.
    """
    # Superuser has all permissions
    if user.is_superuser:
        return [p for p in vars(Permissions).values() if not p.startswith("_")]

    # Team-specific permissions
    if team:
        try:
            team_member = TeamMember.objects.get(
                team=team, organization_member__user=user
            )
            return _get_permissions_for_role(team_member.role)
        except TeamMember.DoesNotExist:
            return []

    # Workspace-specific permissions - combine permissions across all teams
    if workspace:
        all_permissions = set()
        team_members = TeamMember.objects.filter(
            organization_member__user=user, team__workspace_teams__workspace=workspace
        )

        for team_member in team_members:
            all_permissions.update(_get_permissions_for_role(team_member.role))

        return list(all_permissions)

    # No context provided
    return []


def _get_permissions_for_role(role):
    """
    Get all permissions for a specific role.
    """
    all_permissions = [p for p in vars(Permissions).values() if not p.startswith("_")]
    return [p for p in all_permissions if _role_has_permission(role, p)]


def has_permission(*, user, permission, workspace=None, team=None):
    """
    Check if a user has a specific permission without raising exceptions.
    """
    if user.is_superuser:
        return True

    if team:
        try:
            team_member = TeamMember.objects.get(
                team=team, organization_member__user=user
            )
            return _role_has_permission(team_member.role, permission)
        except TeamMember.DoesNotExist:
            return False

    if workspace:
        team_members = TeamMember.objects.filter(
            organization_member__user=user, team__workspace_teams__workspace=workspace
        )

        for team_member in team_members:
            if _role_has_permission(team_member.role, permission):
                return True

    return False
