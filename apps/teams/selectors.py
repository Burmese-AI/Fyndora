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

    return TeamMember.objects.get(team_member_id=team_member_id)
