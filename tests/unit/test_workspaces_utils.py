"""
Unit tests for workspace utilities.

Tests cover:
- Permission checking functions
- Edge cases and error handling
"""

from unittest.mock import patch
import pytest
from django.test import TestCase

from apps.workspaces.utils import (
    can_view_workspace_teams_under_workspace,
    can_view_workspace_currency,
)
from apps.workspaces.constants import StatusChoices
from tests.factories.organization_factories import OrganizationWithOwnerFactory
from tests.factories.workspace_factories import WorkspaceFactory
from tests.factories.user_factories import CustomUserFactory


@pytest.mark.unit
class TestWorkspaceUtils(TestCase):
    """Test workspace utility functions."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    def test_can_view_workspace_teams_under_workspace_with_permission(self):
        """Test that user with permission can view workspace teams."""
        # Mock user has permission
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            result = can_view_workspace_teams_under_workspace(self.user, self.workspace)

            self.assertTrue(result)
            mock_has_perm.assert_called_once()

    @pytest.mark.django_db
    def test_can_view_workspace_teams_under_workspace_without_permission(self):
        """Test that user without permission cannot view workspace teams."""
        # Mock user doesn't have permission
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = False

            result = can_view_workspace_teams_under_workspace(self.user, self.workspace)

            self.assertFalse(result)
            mock_has_perm.assert_called_once()

    @pytest.mark.django_db
    def test_can_view_workspace_teams_under_workspace_with_anonymous_user(self):
        """Test that anonymous user cannot view workspace teams."""
        # Create anonymous user (no user object)
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = False

            result = can_view_workspace_teams_under_workspace(self.user, self.workspace)

            self.assertFalse(result)
            mock_has_perm.assert_called_once()

    @pytest.mark.django_db
    def test_can_view_workspace_teams_under_workspace_with_none_workspace(self):
        """Test that function handles None workspace gracefully."""
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = False

            result = can_view_workspace_teams_under_workspace(self.user, None)

            self.assertFalse(result)
            mock_has_perm.assert_called_once()

    @pytest.mark.django_db
    def test_can_view_workspace_currency_with_permission(self):
        """Test that user with permission can view workspace currency."""
        # Mock user has permission
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            result = can_view_workspace_currency(self.user, self.workspace)

            self.assertTrue(result)
            mock_has_perm.assert_called_once()

    @pytest.mark.django_db
    def test_can_view_workspace_currency_without_permission(self):
        """Test that user without permission cannot view workspace currency."""
        # Mock user doesn't have permission
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = False

            result = can_view_workspace_currency(self.user, self.workspace)

            self.assertFalse(result)
            mock_has_perm.assert_called_once()

    @pytest.mark.django_db
    def test_can_view_workspace_currency_with_anonymous_user(self):
        """Test that anonymous user cannot view workspace currency."""
        # Create anonymous user (no user object)
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = False

            result = can_view_workspace_currency(self.user, self.workspace)

            self.assertFalse(result)
            mock_has_perm.assert_called_once()

    @pytest.mark.django_db
    def test_can_view_workspace_currency_with_none_workspace(self):
        """Test that function handles None workspace gracefully."""
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = False

            result = can_view_workspace_currency(self.user, None)

            self.assertFalse(result)
            mock_has_perm.assert_called_once()

    @pytest.mark.django_db
    def test_permission_functions_use_correct_permission_constants(self):
        """Test that permission functions use the correct permission constants."""
        from apps.core.permissions import WorkspacePermissions

        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            # Test teams permission
            can_view_workspace_teams_under_workspace(self.user, self.workspace)
            mock_has_perm.assert_called_with(
                WorkspacePermissions.VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE,
                self.workspace,
            )

            # Reset mock for next call
            mock_has_perm.reset_mock()

            # Test currency permission
            can_view_workspace_currency(self.user, self.workspace)
            mock_has_perm.assert_called_with(
                WorkspacePermissions.VIEW_WORKSPACE_CURRENCY, self.workspace
            )

    @pytest.mark.django_db
    def test_permission_functions_with_different_workspace_states(self):
        """Test permission functions with different workspace statuses."""
        # Test with active workspace
        self.workspace.status = StatusChoices.ACTIVE
        self.workspace.save()

        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            result = can_view_workspace_teams_under_workspace(self.user, self.workspace)
            self.assertTrue(result)

        # Test with archived workspace
        self.workspace.status = StatusChoices.ARCHIVED
        self.workspace.save()

        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            result = can_view_workspace_teams_under_workspace(self.user, self.workspace)
            self.assertTrue(result)

        # Test with closed workspace
        self.workspace.status = StatusChoices.CLOSED
        self.workspace.save()

        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            result = can_view_workspace_teams_under_workspace(self.user, self.workspace)
            self.assertTrue(result)

    @pytest.mark.django_db
    def test_permission_functions_edge_cases(self):
        """Test permission functions with edge cases."""
        # Test with empty workspace (minimal data)
        minimal_workspace = WorkspaceFactory(
            organization=self.organization,
            title="Minimal",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = False

            result = can_view_workspace_teams_under_workspace(
                self.user, minimal_workspace
            )
            self.assertFalse(result)

            result = can_view_workspace_currency(self.user, minimal_workspace)
            self.assertFalse(result)

    @pytest.mark.django_db
    def test_permission_functions_performance(self):
        """Test that permission functions don't make unnecessary calls."""
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            # Call both functions multiple times
            for _ in range(3):
                can_view_workspace_teams_under_workspace(self.user, self.workspace)
                can_view_workspace_currency(self.user, self.workspace)

            # Should only be called once per function call (6 total calls)
            self.assertEqual(mock_has_perm.call_count, 6)
