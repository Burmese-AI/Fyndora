from guardian.shortcuts import assign_perm
from apps.core.permissions import TeamPermissions
from django.contrib.auth.models import Group
from apps.core.roles import get_permissions_for_role

def assign_team_permissions(team):
   team_coordinator_group_name = f"Team Coordinator - {team.team_id}"
 

   team_coordinator_group, _ = Group.objects.get_or_create(
    name=team_coordinator_group_name
   )

   team_coordinator_permissions = get_permissions_for_role("TEAM_COORDINATOR")

   try:
        for perm in team_coordinator_permissions:
            assign_perm(perm, team_coordinator_group, team)

        if team.team_coordinator is not None:
            team_coordinator_group.user_set.add(team.team_coordinator.user)

        if team.organization.owner is not None:
            team_coordinator_group.user_set.add(team.organization.owner.user)

        print(f"Assigned permissions to {team_coordinator_group} for {team}")
   except Exception as e:
        print(f"Error assigning team permissions: {e}")
        raise e
    
    



