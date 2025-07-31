"""
Unit tests for Team permissions.
"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from apps.teams.permissions import (
    assign_team_permissions,
    check_add_team_member_permission,
    check_add_team_permission,
    check_change_team_permission,
    check_delete_team_permission,
    check_view_team_permission,
    remove_team_permissions,
    update_team_coordinator_group,
)
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory
from tests.factories.user_factories import CustomUserFactory

User = get_user_model()


class TeamPermissionsTest(TestCase):
    """Test team permission functions."""

    def setUp(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.team = TeamFactory(
            organization=self.organization, team_coordinator=self.org_member
        )

    @patch("apps.teams.permissions.assign_perm")
    @patch("apps.teams.permissions.Group.objects.get_or_create")
    def test_assign_team_permissions_success(
        self, mock_get_or_create, mock_assign_perm
    ):
        """Test successful team permission assignment."""
        # Mock group creation
        mock_group = Mock()
        mock_get_or_create.return_value = (mock_group, True)

        # Call the function
        assign_team_permissions(self.team, self.org_member)

        # Verify group was created with correct name
        expected_group_name = f"team_{self.team.team_id}_coordinators"
        mock_get_or_create.assert_called_once_with(name=expected_group_name)

        # Verify user was added to group
        mock_group.user_set.add.assert_called_once_with(self.org_member.user)

        # Verify permissions were assigned
        expected_permissions = [
            "change_team",
            "delete_team",
            "add_teammember",
            "change_teammember",
            "delete_teammember",
        ]

        self.assertEqual(mock_assign_perm.call_count, len(expected_permissions))

        # Check each permission call
        for i, perm in enumerate(expected_permissions):
            call_args = mock_assign_perm.call_args_list[i]
            self.assertEqual(call_args[0], (perm, mock_group, self.team))

    @patch("apps.teams.permissions.assign_perm")
    @patch("apps.teams.permissions.Group.objects.get_or_create")
    def test_assign_team_permissions_no_coordinator(
        self, mock_get_or_create, mock_assign_perm
    ):
        """Test team permission assignment with no coordinator."""
        # Mock group creation
        mock_group = Mock()
        mock_get_or_create.return_value = (mock_group, True)

        # Call the function with None coordinator
        assign_team_permissions(self.team, None)

        # Verify group was created
        mock_get_or_create.assert_called_once()

        # Verify no user was added to group
        mock_group.user_set.add.assert_not_called()

        # Verify permissions were still assigned
        self.assertGreater(mock_assign_perm.call_count, 0)

    @patch("apps.teams.permissions.remove_perm")
    @patch("apps.teams.permissions.Group.objects.filter")
    def test_remove_team_permissions_success(self, mock_filter, mock_remove_perm):
        """Test successful team permission removal."""
        # Mock group query
        mock_group = Mock()
        mock_filter.return_value.first.return_value = mock_group

        # Call the function
        remove_team_permissions(self.team)

        # Verify group was queried correctly
        expected_group_name = f"team_{self.team.team_id}_coordinators"
        mock_filter.assert_called_once_with(name=expected_group_name)

        # Verify permissions were removed
        expected_permissions = [
            "change_team",
            "delete_team",
            "add_teammember",
            "change_teammember",
            "delete_teammember",
        ]

        self.assertEqual(mock_remove_perm.call_count, len(expected_permissions))

        # Verify group was deleted
        mock_group.delete.assert_called_once()

    @patch("apps.teams.permissions.Group.objects.filter")
    def test_remove_team_permissions_no_group(self, mock_filter):
        """Test team permission removal when group doesn't exist."""
        # Mock group query returning None
        mock_filter.return_value.first.return_value = None

        # Call the function - should not raise exception
        remove_team_permissions(self.team)

        # Verify group was queried
        mock_filter.assert_called_once()

    @patch("apps.teams.permissions.Group.objects.filter")
    def test_update_team_coordinator_group_success(self, mock_filter):
        """Test successful team coordinator group update."""
        # Mock existing group
        mock_group = Mock()
        mock_filter.return_value.first.return_value = mock_group

        new_coordinator = OrganizationMemberFactory(organization=self.organization)

        # Call the function
        update_team_coordinator_group(self.team, new_coordinator)

        # Verify group was queried
        expected_group_name = f"team_{self.team.team_id}_coordinators"
        mock_filter.assert_called_once_with(name=expected_group_name)

        # Verify users were cleared and new coordinator added
        mock_group.user_set.clear.assert_called_once()
        mock_group.user_set.add.assert_called_once_with(new_coordinator.user)

    @patch("apps.teams.permissions.Group.objects.filter")
    def test_update_team_coordinator_group_no_coordinator(self, mock_filter):
        """Test team coordinator group update with no coordinator."""
        # Mock existing group
        mock_group = Mock()
        mock_filter.return_value.first.return_value = mock_group

        # Call the function with None coordinator
        update_team_coordinator_group(self.team, None)

        # Verify group was queried
        mock_filter.assert_called_once()

        # Verify users were cleared but none added
        mock_group.user_set.clear.assert_called_once()
        mock_group.user_set.add.assert_not_called()

    @patch("apps.teams.permissions.Group.objects.filter")
    def test_update_team_coordinator_group_no_group(self, mock_filter):
        """Test team coordinator group update when group doesn't exist."""
        # Mock group query returning None
        mock_filter.return_value.first.return_value = None

        new_coordinator = OrganizationMemberFactory(organization=self.organization)

        # Call the function - should not raise exception
        update_team_coordinator_group(self.team, new_coordinator)

        # Verify group was queried
        mock_filter.assert_called_once()

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_add_team_permission_has_permission(self, mock_get_user_perms):
        """Test check_add_team_permission when user has permission."""
        # Mock user permissions
        mock_get_user_perms.return_value = ["add_team"]

        result = check_add_team_permission(self.user, self.organization)

        self.assertTrue(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.organization)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_add_team_permission_no_permission(self, mock_get_user_perms):
        """Test check_add_team_permission when user lacks permission."""
        # Mock user permissions without add_team
        mock_get_user_perms.return_value = ["view_team"]

        result = check_add_team_permission(self.user, self.organization)

        self.assertFalse(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.organization)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_change_team_permission_has_permission(self, mock_get_user_perms):
        """Test check_change_team_permission when user has permission."""
        # Mock user permissions
        mock_get_user_perms.return_value = ["change_team"]

        result = check_change_team_permission(self.user, self.team)

        self.assertTrue(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.team)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_change_team_permission_no_permission(self, mock_get_user_perms):
        """Test check_change_team_permission when user lacks permission."""
        # Mock user permissions without change_team
        mock_get_user_perms.return_value = ["view_team"]

        result = check_change_team_permission(self.user, self.team)

        self.assertFalse(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.team)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_delete_team_permission_has_permission(self, mock_get_user_perms):
        """Test check_delete_team_permission when user has permission."""
        # Mock user permissions
        mock_get_user_perms.return_value = ["delete_team"]

        result = check_delete_team_permission(self.user, self.team)

        self.assertTrue(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.team)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_delete_team_permission_no_permission(self, mock_get_user_perms):
        """Test check_delete_team_permission when user lacks permission."""
        # Mock user permissions without delete_team
        mock_get_user_perms.return_value = ["view_team"]

        result = check_delete_team_permission(self.user, self.team)

        self.assertFalse(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.team)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_add_team_member_permission_has_permission(self, mock_get_user_perms):
        """Test check_add_team_member_permission when user has permission."""
        # Mock user permissions
        mock_get_user_perms.return_value = ["add_teammember"]

        result = check_add_team_member_permission(self.user, self.team)

        self.assertTrue(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.team)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_add_team_member_permission_no_permission(self, mock_get_user_perms):
        """Test check_add_team_member_permission when user lacks permission."""
        # Mock user permissions without add_teammember
        mock_get_user_perms.return_value = ["view_team"]

        result = check_add_team_member_permission(self.user, self.team)

        self.assertFalse(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.team)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_view_team_permission_has_permission(self, mock_get_user_perms):
        """Test check_view_team_permission when user has permission."""
        # Mock user permissions
        mock_get_user_perms.return_value = ["view_team"]

        result = check_view_team_permission(self.user, self.team)

        self.assertTrue(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.team)

    @patch("apps.teams.permissions.get_user_perms")
    def test_check_view_team_permission_no_permission(self, mock_get_user_perms):
        """Test check_view_team_permission when user lacks permission."""
        # Mock user permissions without view_team
        mock_get_user_perms.return_value = []

        result = check_view_team_permission(self.user, self.team)

        self.assertFalse(result)
        mock_get_user_perms.assert_called_once_with(self.user, self.team)

    def test_permission_functions_with_none_inputs(self):
        """Test permission functions handle None inputs gracefully."""
        # These should not raise exceptions
        assign_team_permissions(None, None)
        remove_team_permissions(None)
        update_team_coordinator_group(None, None)

        # These should return False for None inputs
        self.assertFalse(check_add_team_permission(None, None))
        self.assertFalse(check_change_team_permission(None, None))
        self.assertFalse(check_delete_team_permission(None, None))
        self.assertFalse(check_add_team_member_permission(None, None))
        self.assertFalse(check_view_team_permission(None, None))


class TeamPermissionsIntegrationTest(TestCase):
    """Integration tests for team permissions with real objects."""

    def setUp(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.team = TeamFactory(
            organization=self.organization, team_coordinator=self.org_member
        )

    def test_assign_and_remove_permissions_integration(self):
        """Test assigning and removing permissions with real objects."""
        # Assign permissions
        assign_team_permissions(self.team, self.org_member)

        # Verify group was created
        group_name = f"team_{self.team.team_id}_coordinators"
        group = Group.objects.filter(name=group_name).first()
        self.assertIsNotNone(group)

        # Verify user is in group
        self.assertIn(self.user, group.user_set.all())

        # Remove permissions
        remove_team_permissions(self.team)

        # Verify group was deleted
        group = Group.objects.filter(name=group_name).first()
        self.assertIsNone(group)

    def test_update_coordinator_group_integration(self):
        """Test updating coordinator group with real objects."""
        # First assign permissions
        assign_team_permissions(self.team, self.org_member)

        group_name = f"team_{self.team.team_id}_coordinators"
        group = Group.objects.get(name=group_name)

        # Verify initial coordinator is in group
        self.assertIn(self.user, group.user_set.all())

        # Create new coordinator
        new_user = CustomUserFactory()
        new_coordinator = OrganizationMemberFactory(
            organization=self.organization, user=new_user
        )

        # Update coordinator
        update_team_coordinator_group(self.team, new_coordinator)

        # Refresh group
        group.refresh_from_db()

        # Verify old coordinator is removed and new one is added
        self.assertNotIn(self.user, group.user_set.all())
        self.assertIn(new_user, group.user_set.all())

    def test_permission_checks_integration(self):
        """Test permission checks with real objects and permissions."""
        # Initially user should not have permissions
        self.assertFalse(check_change_team_permission(self.user, self.team))
        self.assertFalse(check_delete_team_permission(self.user, self.team))
        self.assertFalse(check_add_team_member_permission(self.user, self.team))

        # Assign permissions
        assign_team_permissions(self.team, self.org_member)

        # Now user should have permissions
        self.assertTrue(check_change_team_permission(self.user, self.team))
        self.assertTrue(check_delete_team_permission(self.user, self.team))
        self.assertTrue(check_add_team_member_permission(self.user, self.team))

        # Remove permissions
        remove_team_permissions(self.team)

        # User should no longer have permissions
        self.assertFalse(check_change_team_permission(self.user, self.team))
        self.assertFalse(check_delete_team_permission(self.user, self.team))
        self.assertFalse(check_add_team_member_permission(self.user, self.team))
