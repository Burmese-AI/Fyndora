from apps.teams.models import TeamMember, Team

def get_all_teams():
    try: 
        return Team.objects.all()
    except:
        return Team.objects.none()

def get_all_team_members():
    try:
        return TeamMember.objects.all()
    except Exception:
        return TeamMember.objects.none()