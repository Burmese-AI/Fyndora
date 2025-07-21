from guardian.shortcuts import assign_perm
from apps.core.permissions import TeamPermissions, OrganizationPermissions
from django.contrib.auth.models import Group
from apps.core.roles import get_permissions_for_role
from apps.core.utils import permission_denied_view

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

        print(f"team.organization.owner: {team.organization.owner}")
        if team.organization.owner is not None:
            team_coordinator_group.user_set.add(team.organization.owner.user)
   except Exception as e:
        print(f"Error assigning team permissions: {e}")
        raise e
    
    


# remove the team permissions
def remove_team_permissions(team):
    try:
        team_coordinator_group_name = f"Team Coordinator - {team.team_id}"
        team_coordinator_group = Group.objects.filter(name=team_coordinator_group_name).first()
        if team_coordinator_group:
            team_coordinator_group.delete()
    except Exception as e:
        print(f"Error removing team permissions: {e}")
        raise e



def update_team_coordinator_group(team, previous_coordinator, new_coordinator):
    try:
        if previous_coordinator == new_coordinator:
            return
        
        team_coordinator_group_name = f"Team Coordinator - {team.team_id}"
        team_coordinator_group = Group.objects.filter(name=team_coordinator_group_name).first()
        if previous_coordinator:
            team_coordinator_group.user_set.remove(previous_coordinator.user)
        if new_coordinator:
            team_coordinator_group.user_set.add(new_coordinator.user)
    except Exception as e:
        print(f"Error updating team coordinator group: {e}")
        raise e





def check_add_team_permission(request, organization):
     if not request.user.has_perm(OrganizationPermissions.ADD_TEAM, organization):
            return permission_denied_view(
                request,
                "You do not have permission to create a team in this organization.",
            )
    
def check_change_team_permission(request, team):
    if not request.user.has_perm(TeamPermissions.CHANGE_TEAM, team):
        return permission_denied_view(
            request,
            "You do not have permission to change the team in this organization.",
        )
    
def check_delete_team_permission(request, team):
    if not request.user.has_perm(TeamPermissions.DELETE_TEAM, team):
        return permission_denied_view(
            request,
            "You do not have permission to delete the team in this organization.",
        )
    
def check_add_team_member_permission(request, team):
    if not request.user.has_perm(TeamPermissions.ADD_TEAM_MEMBER, team):
        return permission_denied_view(
            request,
            "You do not have permission to add a team member to this team.",
        )

def check_view_team_permission(request, team):
    if not request.user.has_perm(TeamPermissions.VIEW_TEAM, team):
        return permission_denied_view(
            request,
            "You do not have permission to view the team in this organization.",
        )
    