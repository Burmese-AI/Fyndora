from django.db import transaction
from apps.teams.models import Team
from apps.teams.exceptions import TeamCreationError

@transaction.atomic
def create_team_for_organization(*, form, org_member, organization) -> Team:
   """
   Creates a new team for an organization

   Args:
        form: TeamCreationForm instance
        organization: The organization that the team should be associated with

    Returns:
        Team obj
   """ 
   try:
       team = form.save(commit=False)
       team.created_by = org_member
       team.organization = organization
       team.save()
       return team
   except Exception as e:
       raise TeamCreationError(f"Failed to create team: {str(e)}")