"""
Unit tests for Entry permissions and utilities.

Tests permission checking functions and utility methods for entries.
"""

from unittest.mock import patch

import pytest

from apps.entries.permissions import EntryPermissions
from apps.entries.utils import (
    can_add_org_expense,
    can_add_workspace_expense,
    can_delete_org_expense,
    can_delete_workspace_expense,
    can_update_org_expense,
    can_update_workspace_expense,
    can_view_org_expense,
)
from apps.core.permissions import OrganizationPermissions, WorkspacePermissions
from tests.factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
    WorkspaceFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestOrganizationExpensePermissions:
    """Test organization expense permission utilities."""

    def setup_method(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            user=self.user, organization=self.organization
        )

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_can_view_org_expense_with_permission(self, mock_has_perm):
        """Test can_view_org_expense returns True when user has permission."""
        mock_has_perm.return_value = True

        result = can_view_org_expense(self.user, self.organization)

        assert result is True
        mock_has_perm.assert_called_once_with(
            self.user, OrganizationPermissions.VIEW_ORG_ENTRY, self.organization
        )

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_can_view_org_expense_without_permission(self, mock_has_perm):
        """Test can_view_org_expense returns False when user lacks permission."""
        mock_has_perm.return_value = False

        result = can_view_org_expense(self.user, self.organization)

        assert result is False
        mock_has_perm.assert_called_once_with(
            self.user, OrganizationPermissions.VIEW_ORG_ENTRY, self.organization
        )

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_can_add_org_expense_with_permission(self, mock_has_perm):
        """Test can_add_org_expense returns True when user has permission."""
        mock_has_perm.return_value = True

        result = can_add_org_expense(self.user, self.organization)

        assert result is True
        mock_has_perm.assert_called_once_with(
            self.user, OrganizationPermissions.ADD_ORG_ENTRY, self.organization
        )

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_can_add_org_expense_without_permission(self, mock_has_perm):
        """Test can_add_org_expense returns False when user lacks permission."""
        mock_has_perm.return_value = False

        result = can_add_org_expense(self.user, self.organization)

        assert result is False

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_can_update_org_expense_with_permission(self, mock_has_perm):
        """Test can_update_org_expense returns True when user has permission."""
        mock_has_perm.return_value = True

        result = can_update_org_expense(self.user, self.organization)

        assert result is True
        mock_has_perm.assert_called_once_with(
            self.user, OrganizationPermissions.CHANGE_ORG_ENTRY, self.organization
        )

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_can_update_org_expense_without_permission(self, mock_has_perm):
        """Test can_update_org_expense returns False when user lacks permission."""
        mock_has_perm.return_value = False

        result = can_update_org_expense(self.user, self.organization)

        assert result is False

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_can_delete_org_expense_with_permission(self, mock_has_perm):
        """Test can_delete_org_expense returns True when user has permission."""
        mock_has_perm.return_value = True

        result = can_delete_org_expense(self.user, self.organization)

        assert result is True
        mock_has_perm.assert_called_once_with(
            self.user, OrganizationPermissions.DELETE_ORG_ENTRY, self.organization
        )

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_can_delete_org_expense_without_permission(self, mock_has_perm):
        """Test can_delete_org_expense returns False when user lacks permission."""
        mock_has_perm.return_value = False

        result = can_delete_org_expense(self.user, self.organization)

        assert result is False


@pytest.mark.unit
@pytest.mark.django_db
class TestWorkspaceExpensePermissions:
    """Test workspace expense permission utilities."""

    def setup_method(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.org_member = OrganizationMemberFactory(
            user=self.user, organization=self.organization
        )

    @patch("apps.entries.utils.user_has_workspace_permission")
    def test_can_add_workspace_expense_with_permission(self, mock_has_perm):
        """Test can_add_workspace_expense returns True when user has permission."""
        mock_has_perm.return_value = True

        result = can_add_workspace_expense(self.user, self.workspace)

        assert result is True
        mock_has_perm.assert_called_once_with(
            self.user, WorkspacePermissions.ADD_WORKSPACE_ENTRY, self.workspace
        )

    @patch("apps.entries.utils.user_has_workspace_permission")
    def test_can_add_workspace_expense_without_permission(self, mock_has_perm):
        """Test can_add_workspace_expense returns False when user lacks permission."""
        mock_has_perm.return_value = False

        result = can_add_workspace_expense(self.user, self.workspace)

        assert result is False

    @patch("apps.entries.utils.user_has_workspace_permission")
    def test_can_update_workspace_expense_with_permission(self, mock_has_perm):
        """Test can_update_workspace_expense returns True when user has permission."""
        mock_has_perm.return_value = True

        result = can_update_workspace_expense(self.user, self.workspace)

        assert result is True
        mock_has_perm.assert_called_once_with(
            self.user, WorkspacePermissions.CHANGE_WORKSPACE_ENTRY, self.workspace
        )

    @patch("apps.entries.utils.user_has_workspace_permission")
    def test_can_update_workspace_expense_without_permission(self, mock_has_perm):
        """Test can_update_workspace_expense returns False when user lacks permission."""
        mock_has_perm.return_value = False

        result = can_update_workspace_expense(self.user, self.workspace)

        assert result is False

    @patch("apps.entries.utils.user_has_workspace_permission")
    def test_can_delete_workspace_expense_with_permission(self, mock_has_perm):
        """Test can_delete_workspace_expense returns True when user has permission."""
        mock_has_perm.return_value = True

        result = can_delete_workspace_expense(self.user, self.workspace)

        assert result is True
        mock_has_perm.assert_called_once_with(
            self.user, WorkspacePermissions.DELETE_WORKSPACE_ENTRY, self.workspace
        )

    @patch("apps.entries.utils.user_has_workspace_permission")
    def test_can_delete_workspace_expense_without_permission(self, mock_has_perm):
        """Test can_delete_workspace_expense returns False when user lacks permission."""
        mock_has_perm.return_value = False

        result = can_delete_workspace_expense(self.user, self.workspace)

        assert result is False


@pytest.mark.unit
@pytest.mark.django_db
class TestPermissionUtilityEdgeCases:
    """Test edge cases and error handling in permission utilities."""

    def test_permission_functions_with_none_user(self):
        """Test permission functions handle None user gracefully."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory()

        # All functions should return False for None user
        assert can_view_org_expense(None, organization) is False
        assert can_add_org_expense(None, organization) is False
        assert can_update_org_expense(None, organization) is False
        assert can_delete_org_expense(None, organization) is False
        assert can_add_workspace_expense(None, workspace) is False
        assert can_update_workspace_expense(None, workspace) is False
        assert can_delete_workspace_expense(None, workspace) is False

    def test_permission_functions_with_none_organization(self):
        """Test permission functions handle None organization gracefully."""
        user = CustomUserFactory()

        # All org functions should return False for None organization
        assert can_view_org_expense(user, None) is False
        assert can_add_org_expense(user, None) is False
        assert can_update_org_expense(user, None) is False
        assert can_delete_org_expense(user, None) is False

    def test_permission_functions_with_none_workspace(self):
        """Test permission functions handle None workspace gracefully."""
        user = CustomUserFactory()

        # All workspace functions should return False for None workspace
        assert can_add_workspace_expense(user, None) is False
        assert can_update_workspace_expense(user, None) is False
        assert can_delete_workspace_expense(user, None) is False

    @patch("apps.entries.utils.user_has_organization_permission")
    def test_permission_function_handles_exception(self, mock_has_perm):
        """Test permission functions handle exceptions gracefully."""
        mock_has_perm.side_effect = Exception("Database error")

        user = CustomUserFactory()
        organization = OrganizationFactory()

        # Should return False when exception occurs
        result = can_view_org_expense(user, organization)
        assert result is False

    def test_permission_functions_with_anonymous_user(self):
        """Test permission functions with anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        anonymous_user = AnonymousUser()
        organization = OrganizationFactory()
        workspace = WorkspaceFactory()

        # All functions should return False for anonymous user
        assert can_view_org_expense(anonymous_user, organization) is False
        assert can_add_org_expense(anonymous_user, organization) is False
        assert can_update_org_expense(anonymous_user, organization) is False
        assert can_delete_org_expense(anonymous_user, organization) is False
        assert can_add_workspace_expense(anonymous_user, workspace) is False
        assert can_update_workspace_expense(anonymous_user, workspace) is False
        assert can_delete_workspace_expense(anonymous_user, workspace) is False


@pytest.mark.unit
class TestEntryPermissionsConstants:
    """Test Entry permissions constants."""

    def test_entry_permissions_choices(self):
        """Test EntryPermissions contains expected choices."""
        expected_permissions = [
            "workspaces.add_workspace_entry",
            "workspaces.change_workspace_entry",
            "workspaces.delete_workspace_entry",
            "workspaces.view_workspace_entry",
            "workspaces.review_workspace_entry",
            "workspaces.upload_workspace_attachments",
            "workspaces.flag_workspace_entry",
        ]

        permission_values = [choice[0] for choice in EntryPermissions.choices]

        for perm in expected_permissions:
            assert perm in permission_values

    def test_entry_permissions_labels(self):
        """Test EntryPermissions have proper labels."""
        permission_dict = dict(EntryPermissions.choices)

        # Check some key permissions have proper labels
        assert "Can add entry to workspace" in permission_dict.values()
        assert "Can change entry in workspace" in permission_dict.values()
        assert "Can delete entry in workspace" in permission_dict.values()
        assert "Can view entry in workspace" in permission_dict.values()
        assert "Can review entry in workspace" in permission_dict.values()

    def test_entry_permissions_constants_exist(self):
        """Test EntryPermissions constants are accessible."""
        # Test that constants can be accessed
        assert hasattr(EntryPermissions, "ADD_ENTRY")
        assert hasattr(EntryPermissions, "CHANGE_ENTRY")
        assert hasattr(EntryPermissions, "DELETE_ENTRY")
        assert hasattr(EntryPermissions, "VIEW_ENTRY")
        assert hasattr(EntryPermissions, "REVIEW_ENTRY")
        assert hasattr(EntryPermissions, "UPLOAD_ATTACHMENTS")
        assert hasattr(EntryPermissions, "FLAG_ENTRY")

    def test_entry_permissions_values(self):
        """Test EntryPermissions have expected values."""
        assert EntryPermissions.ADD_ENTRY == "workspaces.add_workspace_entry"
        assert EntryPermissions.CHANGE_ENTRY == "workspaces.change_workspace_entry"
        assert EntryPermissions.DELETE_ENTRY == "workspaces.delete_workspace_entry"
        assert EntryPermissions.VIEW_ENTRY == "workspaces.view_workspace_entry"
        assert EntryPermissions.REVIEW_ENTRY == "workspaces.review_workspace_entry"
        assert EntryPermissions.UPLOAD_ATTACHMENTS == "workspaces.upload_workspace_attachments"
        assert EntryPermissions.FLAG_ENTRY == "workspaces.flag_workspace_entry"


@pytest.mark.unit
@pytest.mark.django_db
class TestPermissionIntegration:
    """Test permission utilities integration with actual permission system."""

    def setup_method(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)

    def test_permission_utilities_call_correct_functions(self):
        """Test that permission utilities call the correct underlying functions."""
        with patch(
            "apps.entries.utils.user_has_organization_permission"
        ) as mock_org_perm:
            with patch(
                "apps.entries.utils.user_has_workspace_permission"
            ) as mock_workspace_perm:
                mock_org_perm.return_value = True
                mock_workspace_perm.return_value = True

                # Test organization permissions
                can_view_org_expense(self.user, self.organization)
                can_add_org_expense(self.user, self.organization)
                can_update_org_expense(self.user, self.organization)
                can_delete_org_expense(self.user, self.organization)

                # Test workspace permissions
                can_add_workspace_expense(self.user, self.workspace)
                can_update_workspace_expense(self.user, self.workspace)
                can_delete_workspace_expense(self.user, self.workspace)

                # Verify correct number of calls
                assert mock_org_perm.call_count == 4
                assert mock_workspace_perm.call_count == 3

    def test_permission_utilities_with_real_permission_system(self):
        """Test permission utilities work with real permission assignments."""
        from guardian.shortcuts import assign_perm, remove_perm

        # Test without permissions
        assert can_view_org_expense(self.user, self.organization) is False

        # Assign permission and test
        assign_perm(
            OrganizationPermissions.VIEW_ORG_ENTRY, self.user, self.organization
        )
        assert can_view_org_expense(self.user, self.organization) is True

        # Remove permission and test
        remove_perm(
            OrganizationPermissions.VIEW_ORG_ENTRY, self.user, self.organization
        )
        assert can_view_org_expense(self.user, self.organization) is False
