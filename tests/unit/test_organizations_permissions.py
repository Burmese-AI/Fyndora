"""Unit tests for organization permissions.

Tests permission checking functions with various scenarios and edge cases.
"""

from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser

from apps.organizations.permissions import can_remove_org_member
from apps.core.permissions import OrganizationPermissions
from tests.factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
)


class TestCanRemoveOrgMember(TestCase):
    """Test can_remove_org_member permission function."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )

    def test_can_remove_org_member_with_permission(self):
        """Test that user can remove org member when they have the permission."""
        # Mock user.has_perm to return True
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            result = can_remove_org_member(self.user, self.organization)

            # Verify the permission was checked correctly
            mock_has_perm.assert_called_once_with(
                OrganizationPermissions.REMOVE_ORG_MEMBER, self.organization
            )
            self.assertTrue(result)

    def test_can_remove_org_member_without_permission(self):
        """Test that user cannot remove org member when they don't have the permission."""
        # Mock user.has_perm to return False
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = False

            result = can_remove_org_member(self.user, self.organization)

            # Verify the permission was checked correctly
            mock_has_perm.assert_called_once_with(
                OrganizationPermissions.REMOVE_ORG_MEMBER, self.organization
            )
            self.assertFalse(result)

    def test_can_remove_org_member_anonymous_user(self):
        """Test that anonymous user cannot remove org member."""
        anonymous_user = AnonymousUser()

        result = can_remove_org_member(anonymous_user, self.organization)

        # Anonymous users should not have permissions
        self.assertFalse(result)

    def test_can_remove_org_member_none_user(self):
        """Test that None user cannot remove org member."""
        result = can_remove_org_member(None, self.organization)

        # None user should not have permissions
        self.assertFalse(result)

    def test_can_remove_org_member_none_organization(self):
        """Test that user cannot remove org member from None organization."""
        result = can_remove_org_member(self.user, None)

        # None organization should not grant permissions
        self.assertFalse(result)

    def test_can_remove_org_member_both_none(self):
        """Test that None user cannot remove org member from None organization."""
        result = can_remove_org_member(None, None)

        # Both None should not grant permissions
        self.assertFalse(result)

    def test_can_remove_org_member_permission_string_value(self):
        """Test that the correct permission string is used."""
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            can_remove_org_member(self.user, self.organization)

            # Verify the exact permission string is used
            expected_permission = OrganizationPermissions.REMOVE_ORG_MEMBER
            mock_has_perm.assert_called_once_with(
                expected_permission, self.organization
            )

            # Verify the permission string value
            self.assertEqual(expected_permission, "remove_org_member")

    def test_can_remove_org_member_different_organizations(self):
        """Test that permissions are organization-specific."""
        other_organization = OrganizationFactory()

        with patch.object(self.user, "has_perm") as mock_has_perm:
            # Mock different permissions for different organizations
            mock_has_perm.side_effect = lambda perm, org: (
                perm == OrganizationPermissions.REMOVE_ORG_MEMBER
                and org == self.organization
            )

            # Should have permission for first organization
            result1 = can_remove_org_member(self.user, self.organization)
            self.assertTrue(result1)

            # Should not have permission for other organization
            result2 = can_remove_org_member(self.user, other_organization)
            self.assertFalse(result2)

    def test_can_remove_org_member_multiple_calls(self):
        """Test that multiple calls work correctly."""
        with patch.object(self.user, "has_perm") as mock_has_perm:
            mock_has_perm.return_value = True

            # First call
            result1 = can_remove_org_member(self.user, self.organization)
            self.assertTrue(result1)

            # Second call
            result2 = can_remove_org_member(self.user, self.organization)
            self.assertTrue(result2)

            # Verify has_perm was called twice
            self.assertEqual(mock_has_perm.call_count, 2)

    def test_can_remove_org_member_with_organization_member_object(self):
        """Test that the function works with organization member objects."""
        # Test with the organization member object itself
        result = can_remove_org_member(self.user, self.organization_member.organization)

        # Should work the same as with organization directly
        self.assertFalse(
            result
        )  # Since we're not mocking has_perm, it will return False

    def test_can_remove_org_member_permission_label(self):
        """Test that the permission has the correct label."""
        permission = OrganizationPermissions.REMOVE_ORG_MEMBER
        self.assertEqual(
            permission.label,
            "Can remove org member from organization only by Org Owner",
        )
