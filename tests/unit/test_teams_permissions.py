"""
Unit tests for Team permissions.
"""

from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import Group

from apps.teams.permissions import (
    assign_team_permissions,
    remove_team_permissions,
    update_team_coordinator_group,
    check_add_team_permission,
    check_change_team_permission,
    check_delete_team_permission,
    check_add_team_member_permission,
    check_view_team_permission,
)
from apps.core.permissions import (
    TeamPermissions,
    OrganizationPermissions,
)
from tests.factories.organization_factories import (
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory
from tests.factories.user_factories import CustomUserFactory


class TeamPermissionsTest(TestCase):
    """Test cases for Team permissions."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.user = CustomUserFactory()
        self.request_factory = RequestFactory()

    @patch("apps.teams.permissions.get_permissions_for_role")
    @patch("apps.teams.permissions.assign_perm")
    def test_assign_team_permissions_success(
        self, mock_assign_perm, mock_get_permissions
    ):
        """Test successful team permissions assignment."""
        # Mock permissions for team coordinator role
        mock_permissions = [
            OrganizationPermissions.MANAGE_ORGANIZATION,
            TeamPermissions.ADD_TEAM_MEMBER,
            TeamPermissions.VIEW_TEAM,
        ]
        mock_get_permissions.return_value = mock_permissions

        # Set team coordinator
        self.team.team_coordinator = self.org_member
        self.team.save()

        assign_team_permissions(self.team)

        # Verify group was created
        group_name = f"Team Coordinator - {self.team.team_id}"
        group = Group.objects.filter(name=group_name).first()
        self.assertIsNotNone(group)

        # Verify permissions were assigned
        mock_assign_perm.assert_called()

        # Verify team coordinator was added to group
        self.assertIn(self.org_member.user, group.user_set.all())

        # Verify organization owner was added to group
        if self.organization.owner:
            self.assertIn(self.organization.owner.user, group.user_set.all())

    @patch("apps.teams.permissions.get_permissions_for_role")
    @patch("apps.teams.permissions.assign_perm")
    def test_assign_team_permissions_without_coordinator(
        self, mock_assign_perm, mock_get_permissions
    ):
        """Test team permissions assignment without coordinator."""
        # Mock permissions for team coordinator role
        mock_permissions = [
            OrganizationPermissions.MANAGE_ORGANIZATION,
            TeamPermissions.ADD_TEAM_MEMBER,
        ]
        mock_get_permissions.return_value = mock_permissions

        # No team coordinator
        self.team.team_coordinator = None
        self.team.save()

        assign_team_permissions(self.team)

        # Verify group was created
        group_name = f"Team Coordinator - {self.team.team_id}"
        group = Group.objects.filter(name=group_name).first()
        self.assertIsNotNone(group)

        # Verify permissions were assigned
        mock_assign_perm.assert_called()

        # Verify only organization owner was added to group
        if self.organization.owner:
            self.assertIn(self.organization.owner.user, group.user_set.all())

    @patch("apps.teams.permissions.get_permissions_for_role")
    @patch("apps.teams.permissions.assign_perm")
    def test_assign_team_permissions_exception_handling(
        self, mock_assign_perm, mock_get_permissions
    ):
        """Test team permissions assignment exception handling."""
        # Mock permissions for team coordinator role
        mock_permissions = [TeamPermissions.ADD_TEAM_MEMBER]
        mock_get_permissions.return_value = mock_permissions

        # Mock assign_perm to raise an exception
        mock_assign_perm.side_effect = Exception("Permission assignment failed")

        with self.assertRaises(Exception):
            assign_team_permissions(self.team)

    def test_remove_team_permissions_success(self):
        """Test successful team permissions removal."""
        # Create a group first
        group_name = f"Team Coordinator - {self.team.team_id}"
        Group.objects.create(name=group_name)

        remove_team_permissions(self.team)

        # Verify group was deleted
        self.assertFalse(Group.objects.filter(name=group_name).exists())

    def test_remove_team_permissions_group_not_found(self):
        """Test team permissions removal when group doesn't exist."""
        # No group exists
        remove_team_permissions(self.team)

        # Should not raise an exception
        self.assertTrue(True)

    @patch("apps.teams.permissions.remove_perm")
    def test_update_team_coordinator_group_same_coordinator(self, mock_remove_perm):
        """Test updating team coordinator group when coordinator doesn't change."""
        # Same coordinator
        previous_coordinator = self.org_member
        new_coordinator = self.org_member

        update_team_coordinator_group(self.team, previous_coordinator, new_coordinator)

        # Should return early without doing anything
        mock_remove_perm.assert_not_called()

    @patch("apps.teams.permissions.remove_perm")
    def test_update_team_coordinator_group_remove_previous(self, mock_remove_perm):
        """Test updating team coordinator group when removing previous coordinator."""
        # Create a group first
        group_name = f"Team Coordinator - {self.team.team_id}"
        group = Group.objects.create(name=group_name)
        group.user_set.add(self.org_member.user)

        previous_coordinator = self.org_member
        new_coordinator = None

        update_team_coordinator_group(self.team, previous_coordinator, new_coordinator)

        # Verify previous coordinator was removed from group
        self.assertNotIn(self.org_member.user, group.user_set.all())

    @patch("apps.teams.permissions.remove_perm")
    def test_update_team_coordinator_group_add_new(self, mock_remove_perm):
        """Test updating team coordinator group when adding new coordinator."""
        # Create a group first
        group_name = f"Team Coordinator - {self.team.team_id}"
        group = Group.objects.create(name=group_name)

        previous_coordinator = None
        new_coordinator = self.org_member

        update_team_coordinator_group(self.team, previous_coordinator, new_coordinator)

        # Verify new coordinator was added to group
        self.assertIn(self.org_member.user, group.user_set.all())

    @patch("apps.teams.permissions.remove_perm")
    def test_update_team_coordinator_group_replace_coordinator(self, mock_remove_perm):
        """Test updating team coordinator group when replacing coordinator."""
        # Create a group first
        group_name = f"Team Coordinator - {self.team.team_id}"
        group = Group.objects.create(name=group_name)
        group.user_set.add(self.org_member.user)

        # Create a new coordinator
        new_coordinator = OrganizationMemberFactory(organization=self.organization)
        group.user_set.add(new_coordinator.user)

        previous_coordinator = self.org_member

        update_team_coordinator_group(self.team, previous_coordinator, new_coordinator)

        # Verify previous coordinator was removed
        self.assertNotIn(self.org_member.user, group.user_set.all())
        # Verify new coordinator remains
        self.assertIn(new_coordinator.user, group.user_set.all())

    @patch("apps.teams.permissions.remove_perm")
    def test_update_team_coordinator_group_exception_handling(self, mock_remove_perm):
        """Test updating team coordinator group exception handling."""
        # Mock remove_perm to raise an exception
        mock_remove_perm.side_effect = Exception("Permission removal failed")

        previous_coordinator = self.org_member
        new_coordinator = None

        with self.assertRaises(Exception):
            update_team_coordinator_group(
                self.team, previous_coordinator, new_coordinator
            )


class TeamPermissionChecksTest(TestCase):
    """Test cases for Team permission check functions."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.user = CustomUserFactory()
        self.request_factory = RequestFactory()

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_add_team_permission_success(self, mock_permission_denied):
        """Test successful add team permission check."""
        # Mock user has permission
        with patch.object(self.user, "has_perm", return_value=True):
            request = self.request_factory.get("/")
            request.user = self.user

            result = check_add_team_permission(request, self.organization)

            # Should return None (no permission denied)
            self.assertIsNone(result)
            mock_permission_denied.assert_not_called()

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_add_team_permission_denied(self, mock_permission_denied):
        """Test add team permission check when denied."""
        # Mock user doesn't have permission
        with patch.object(self.user, "has_perm", return_value=False):
            request = self.request_factory.get("/")
            request.user = self.user

            mock_permission_denied.return_value = "Permission Denied"

            result = check_add_team_permission(request, self.organization)

            # Should call permission_denied_view
            mock_permission_denied.assert_called_once()
            self.assertEqual(result, "Permission Denied")

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_change_team_permission_success(self, mock_permission_denied):
        """Test successful change team permission check."""
        # Mock user has permission
        with patch.object(self.user, "has_perm", return_value=True):
            request = self.request_factory.get("/")
            request.user = self.user

            result = check_change_team_permission(request, self.team)

            # Should return None (no permission denied)
            self.assertIsNone(result)
            mock_permission_denied.assert_not_called()

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_change_team_permission_denied(self, mock_permission_denied):
        """Test change team permission check when denied."""
        # Mock user doesn't have permission
        with patch.object(self.user, "has_perm", return_value=False):
            request = self.request_factory.get("/")
            request.user = self.user

            mock_permission_denied.return_value = "Permission Denied"

            result = check_change_team_permission(request, self.team)

            # Should call permission_denied_view
            mock_permission_denied.assert_called_once()
            self.assertEqual(result, "Permission Denied")

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_delete_team_permission_success(self, mock_permission_denied):
        """Test successful delete team permission check."""
        # Mock user has permission
        with patch.object(self.user, "has_perm", return_value=True):
            request = self.request_factory.get("/")
            request.user = self.user

            result = check_delete_team_permission(request, self.team)

            # Should return None (no permission denied)
            self.assertIsNone(result)
            mock_permission_denied.assert_not_called()

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_delete_team_permission_denied(self, mock_permission_denied):
        """Test delete team permission check when denied."""
        # Mock user doesn't have permission
        with patch.object(self.user, "has_perm", return_value=False):
            request = self.request_factory.get("/")
            request.user = self.user

            mock_permission_denied.return_value = "Permission Denied"

            result = check_delete_team_permission(request, self.team)

            # Should call permission_denied_view
            mock_permission_denied.assert_called_once()
            self.assertEqual(result, "Permission Denied")

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_add_team_member_permission_success(self, mock_permission_denied):
        """Test successful add team member permission check."""
        # Mock user has permission
        with patch.object(self.user, "has_perm", return_value=True):
            request = self.request_factory.get("/")
            request.user = self.user

            result = check_add_team_member_permission(request, self.team)

            # Should return None (no permission denied)
            self.assertIsNone(result)
            mock_permission_denied.assert_not_called()

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_add_team_member_permission_denied(self, mock_permission_denied):
        """Test add team member permission check when denied."""
        # Mock user doesn't have permission
        with patch.object(self.user, "has_perm", return_value=False):
            request = self.request_factory.get("/")
            request.user = self.user

            mock_permission_denied.return_value = "Permission Denied"

            result = check_add_team_member_permission(request, self.team)

            # Should call permission_denied_view
            mock_permission_denied.assert_called_once()
            self.assertEqual(result, "Permission Denied")

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_view_team_permission_success(self, mock_permission_denied):
        """Test successful view team permission check."""
        # Mock user has permission
        with patch.object(self.user, "has_perm", return_value=True):
            request = self.request_factory.get("/")
            request.user = self.user

            result = check_view_team_permission(request, self.team)

            # Should return None (no permission denied)
            self.assertIsNone(result)
            mock_permission_denied.assert_not_called()

    @patch("apps.teams.permissions.permission_denied_view")
    def test_check_view_team_permission_denied(self, mock_permission_denied):
        """Test view team permission check when denied."""
        # Mock user doesn't have permission
        with patch.object(self.user, "has_perm", return_value=False):
            request = self.request_factory.get("/")
            request.user = self.user

            mock_permission_denied.return_value = "Permission Denied"

            result = check_view_team_permission(request, self.team)

            # Should call permission_denied_view
            mock_permission_denied.assert_called_once()
            self.assertEqual(result, "Permission Denied")


class TeamPermissionsIntegrationTest(TestCase):
    """Integration tests for Team permissions."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)

    def test_full_permission_lifecycle(self):
        """Test complete permission lifecycle for a team."""
        # Assign permissions
        assign_team_permissions(self.team)

        # Verify group was created
        group_name = f"Team Coordinator - {self.team.team_id}"
        group = Group.objects.filter(name=group_name).first()
        self.assertIsNotNone(group)

        # Verify organization owner was added
        if self.organization.owner:
            self.assertIn(self.organization.owner.user, group.user_set.all())

        # Remove permissions
        remove_team_permissions(self.team)

        # Verify group was deleted
        self.assertFalse(Group.objects.filter(name=group_name).exists())

    def test_coordinator_permission_workflow(self):
        """Test coordinator permission workflow."""
        # Create initial coordinator
        initial_coordinator = self.org_member
        self.team.team_coordinator = initial_coordinator
        self.team.save()

        # Assign permissions
        assign_team_permissions(self.team)

        # Verify initial coordinator is in group
        group_name = f"Team Coordinator - {self.team.team_id}"
        group = Group.objects.filter(name=group_name).first()
        self.assertIn(initial_coordinator.user, group.user_set.all())

        # Create new coordinator
        new_coordinator = OrganizationMemberFactory(organization=self.organization)

        # Update coordinator group
        update_team_coordinator_group(self.team, initial_coordinator, new_coordinator)

        # Verify old coordinator was removed
        self.assertNotIn(initial_coordinator.user, group.user_set.all())
        # Verify new coordinator was added
        self.assertIn(new_coordinator.user, group.user_set.all())

        # Clean up
        remove_team_permissions(self.team)
