from apps.teams.exceptions import TeamCreationError


def create_team_from_form(form, organization):
    try:
        team = form.save(commit=False)
        team.organization = organization
        team.save()
        return team
    except Exception as e:
        raise TeamCreationError(f"An error occurred while creating team: {str(e)}")
