def create_team_from_form(form, organization):
    team = form.save(commit=False)
    team.organization = organization
    team.save()
    return team
