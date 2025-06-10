from apps.teams.models import TeamMember


def get_all_team_members():
    try:
        return TeamMember.objects.all()
    except Exception:
        return TeamMember.objects.none()
