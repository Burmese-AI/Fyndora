from apps.teams.models import TeamMember, Team


def get_team_members(team=None, prefetch_user=False):
    """
    Returns all team members.
    """
    queryset = TeamMember.objects.all()
    if team:
        queryset = queryset.filter(team=team)
    if prefetch_user:
        queryset = queryset.select_related("organization_member__user")
    return queryset


def get_all_team_members():
    try:
        return TeamMember.objects.all()
    except Exception:
        return TeamMember.objects.none()


def get_teams_by_organization_id(organization_id):
    """
    Get all teams by organization ID.
    """
    try:
        return Team.objects.filter(organization_id=organization_id)
    except Exception:
        return Team.objects.none()


def get_team_by_id(team_id):
    """
    Get a team by its ID.
    """
    try:
        return Team.objects.get(team_id=team_id)
    except Team.DoesNotExist:
        return None
    except Exception:
        return None


def get_team_member_by_id(team_member_id):
    """
    Get a team member by its ID.
    """
    try:
        return TeamMember.objects.get(team_member_id=team_member_id)
    except TeamMember.DoesNotExist:
        return None


def get_team_members_by_team_id(team_id):
    """
    Get all team members by team ID.
    """
    try:
        return TeamMember.objects.filter(team_id=team_id)
    except Exception:
        return TeamMember.objects.none()
