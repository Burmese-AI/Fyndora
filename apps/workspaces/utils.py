from apps.core.permissions import WorkspacePermissions


def can_view_workspace_teams_under_workspace(user, workspace):
    if user.has_perm(
        WorkspacePermissions.VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE, workspace
    ):
        return True
    return False
