from apps.teams.models import TeamMember, Team


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
