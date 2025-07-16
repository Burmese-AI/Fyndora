from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm
from .roles import Role


class ObjectPermissionManager:
    """
    Helper for managing per-object permissions using groups.
    Just plug in an object and use role-based permission handling.
    """
    allowed_roles = []

    def __init__(self, obj):
        # The object we're assigning permissions for
        self.obj = obj

    def get_group_name(self, role_name: Role) -> str:
        # like "ORG_OWNER - 123" based on role and object ID
        return f"{role_name.value} - {self.obj.pk}"

    def assign_role_permissions(self, role_name: Role):
        """
        Assign the right perms to the group based on role.
        """
        self._validate_role(role_name)
        from .roles import ROLE_PERMISSIONS
        perms = ROLE_PERMISSIONS.get(role_name.value, [])
        group = self._get_or_create_group(role_name)
        for perm in perms:
            assign_perm(perm, group, self.obj)

    def sync_role_members(self, role_name: Role, old_user, new_user):
        """
        Replace old user with new one in the role group.
        If there's no old user or no change, just adds the new one.
        """
        self._validate_role(role_name)
        group = self._get_or_create_group(role_name)
        if old_user and old_user != new_user:
            group.user_set.remove(old_user)
        if new_user:
            group.user_set.add(new_user)

    def user_has_perm(self, user, perm_codename):
        """
        Check if the user has this object-specific permission.
        """
        return user.has_perm(perm_codename, self.obj)

    def _get_or_create_group(self, role_name: Role) -> Group:
        """
        Get or create a group for this role and object.
        """
        self._validate_role(role_name)
        group_name = self.get_group_name(role_name)
        group, _ = Group.objects.get_or_create(name=group_name)
        return group

    def _validate_role(self, role_name: Role):
        """
        Make sure the role is allowed for this manager.
        """
        if role_name.value not in self.allowed_roles:
            raise ValueError(f"Role '{role_name.value}' is not allowed. Allowed roles: {self.allowed_roles}")
