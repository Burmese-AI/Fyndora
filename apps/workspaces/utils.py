from apps.core.permissions import WorkspacePermissions


def can_view_workspace_teams_under_workspace(user, workspace):
    if user.has_perm(
        WorkspacePermissions.VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE, workspace
    ):
        return True
    return False

def can_view_workspace_currency(user, workspace):
    if user.has_perm(WorkspacePermissions.VIEW_WORKSPACE_CURRENCY, workspace):
        return True
    return False