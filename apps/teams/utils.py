from django.contrib.auth.models import Group

def add_user_to_workspace_team_group(joined_workspace_teams, new_team_member):
    for workspace_team in joined_workspace_teams:
        workspace_team_group_name = f"Workspace Team - {workspace_team.workspace_team_id}"
        workspace_team_group = Group.objects.filter(name=workspace_team_group_name).first()
        if workspace_team_group is not None:
            try:
                workspace_team_group.user_set.add(new_team_member.organization_member.user)
            except Exception as e:
                print(f"Error in adding user to workspace_team_group: {str(e)}")
