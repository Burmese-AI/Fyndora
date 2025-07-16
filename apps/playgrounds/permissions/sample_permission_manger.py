from .base import ObjectPermissionManager
from .roles import WORKSPACE_ADMIN_ROLE, OPERATIONS_REVIEWER_ROLE


# Usage 1
class WorkspacePermissionManager(ObjectPermissionManager):
    allowed_roles = [WORKSPACE_ADMIN_ROLE, OPERATIONS_REVIEWER_ROLE]
    
    def __init__(self, obj):
        super().__init__(obj)
        self._setup_permissions()

    def _setup_permissions(self):
        for role in self.allowed_roles:
            self.assign_role_permissions(role)

# Usage 2            
class TeamPermissionManager(ObjectPermissionManager):
    allowed_roles = [TEAM_COORDINATOR_ROLE]
    
    #Without overriding init method, manual assignment of permissions to the group is required
    #E.g. 
    # instance = TeamPermissionManager(team)
    # instance.assign_role_permissions(TEAM_COORDINATOR_ROLE)
