from django.core.exceptions import PermissionDenied

from apps.core.permissions import Permissions
from apps.teams.constants import TeamMemberRole
from apps.teams.models import TeamMember


def check_permission(*, user, permission, workspace=None, team=None):
    """
    Check if user has permission for a given operation.
    Raises PermissionDenied if not authorized.
    """
    if user.is_superuser:
        return True

    if permission in [Permissions.EDIT_ORGANIZATION, Permissions.DELETE_ORGANIZATION]:
        if workspace and hasattr(workspace, "organization"):
            organization = workspace.organization
            if user.has_perm(permission, organization):
                return True
            raise PermissionDenied(
                f"You don't have {permission} permission for this organization"
            )

    # No workspace or team context for workspace permissions
    if not workspace and not team:
        raise ValueError("Either workspace or team context is required")

    # Get team context if only workspace provided
    if workspace and not team:
        # For permissions that only require workspace level, we can skip team check
        workspace_only_permissions = [
            Permissions.VIEW_WORKSPACE,
            Permissions.VIEW_REPORTS,
        ]

        if permission in workspace_only_permissions:
            # Check if user is a member of any team in the workspace
            teams_in_workspace = TeamMember.objects.filter(
                organization_member__user=user,
                team__workspace_teams__workspace=workspace,
            ).exists()

            if teams_in_workspace:
                return True
            raise PermissionDenied("You are not a member of any team in this workspace")

        # For team-specific permissions, get the user's highest role in any team
        team_members = TeamMember.objects.filter(
            organization_member__user=user, team__workspace_teams__workspace=workspace
        )

        if not team_members.exists():
            raise PermissionDenied("You are not a member of any team in this workspace")

        # Check if any of the user's roles have the required permission
        for team_member in team_members:
            try:
                role = team_member.role
                if _role_has_permission(role, permission):
                    return True
            except Exception:
                continue

        raise PermissionDenied(f"You don't have the required permission: {permission}")

    # If team context is provided, check user's role in that team
    if team:
        try:
            team_member = TeamMember.objects.get(
                team=team, organization_member__user=user
            )
            role = team_member.role

            if _role_has_permission(role, permission):
                return True

            raise PermissionDenied(
                f"Your role '{role}' doesn't have the required permission: {permission}"
            )
        except TeamMember.DoesNotExist:
            raise PermissionDenied("You are not a member of this team")

    raise PermissionDenied("Permission denied")


def _role_has_permission(role, permission):
    """
    Check if a role has a specific permission.
    """
    # Permission matrix based on roles
    permission_map = {
        # Workspace Admin
        TeamMemberRole.WORKSPACE_ADMIN: [
            Permissions.CREATE_WORKSPACE,
            Permissions.ASSIGN_TEAMS,
            Permissions.CONFIG_DEADLINES,
            Permissions.VIEW_WORKSPACE,
            Permissions.SUBMIT_ENTRIES,
            Permissions.UPLOAD_ATTACHMENTS,
            Permissions.EDIT_ENTRIES,
            Permissions.REVIEW_ENTRIES,
            Permissions.FLAG_ENTRIES,
            Permissions.VIEW_REPORTS,
            Permissions.EXPORT_REPORTS,
            Permissions.LOCK_WORKSPACE,
        ],
        # Operations Reviewer
        TeamMemberRole.OPERATIONS_REVIEWER: [
            Permissions.VIEW_WORKSPACE,
            Permissions.EDIT_ENTRIES,
            Permissions.REVIEW_ENTRIES,
            Permissions.FLAG_ENTRIES,
            Permissions.VIEW_REPORTS,
            Permissions.EXPORT_REPORTS,
        ],
        # Team Coordinator
        TeamMemberRole.TEAM_COORDINATOR: [
            Permissions.VIEW_WORKSPACE,
            Permissions.SUBMIT_ENTRIES,
            Permissions.UPLOAD_ATTACHMENTS,
            Permissions.EDIT_ENTRIES,
            Permissions.REVIEW_ENTRIES,
            Permissions.FLAG_ENTRIES,
            Permissions.VIEW_REPORTS,
        ],
        # Submitter
        TeamMemberRole.SUBMITTER: [
            Permissions.VIEW_WORKSPACE,
            Permissions.SUBMIT_ENTRIES,
            Permissions.UPLOAD_ATTACHMENTS,
            Permissions.EDIT_ENTRIES,
        ],
        # Auditor
        TeamMemberRole.AUDITOR: [
            Permissions.VIEW_WORKSPACE,
            Permissions.REVIEW_ENTRIES,
            Permissions.FLAG_ENTRIES,
            Permissions.VIEW_REPORTS,
            Permissions.EXPORT_REPORTS,
        ],
    }

    return permission in permission_map.get(role, [])
