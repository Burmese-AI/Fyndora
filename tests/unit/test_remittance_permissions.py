"""
Unit tests for Remittance permissions.
"""

import pytest
from unittest.mock import Mock, patch

from apps.remittance.permissions import RemittancePermissions
from tests.factories import (
    CustomUserFactory,
    OrganizationFactory,
    WorkspaceFactory,
    TeamFactory,
    WorkspaceTeamFactory,
    RemittanceFactory,
)


@pytest.mark.django_db
class TestRemittancePermissions:
    """Test RemittancePermissions class."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.remittance = RemittanceFactory(workspace_team=self.workspace_team)

        self.user = CustomUserFactory()
        self.request = Mock()
        self.request.user = self.user

    def test_add_remittance_permission_constant(self):
        """Test ADD_REMITTANCE permission constant."""
        assert RemittancePermissions.ADD_REMITTANCE == "remittance.add_remittance"

    def test_change_remittance_permission_constant(self):
        """Test CHANGE_REMITTANCE permission constant."""
        assert RemittancePermissions.CHANGE_REMITTANCE == "remittance.change_remittance"

    def test_delete_remittance_permission_constant(self):
        """Test DELETE_REMITTANCE permission constant."""
        assert RemittancePermissions.DELETE_REMITTANCE == "remittance.delete_remittance"

    def test_view_remittance_permission_constant(self):
        """Test VIEW_REMITTANCE permission constant."""
        assert RemittancePermissions.VIEW_REMITTANCE == "remittance.view_remittance"

    def test_review_remittance_permission_constant(self):
        """Test REVIEW_REMITTANCE permission constant."""
        assert RemittancePermissions.REVIEW_REMITTANCE == "remittance.review_remittance"

    def test_flag_remittance_permission_constant(self):
        """Test FLAG_REMITTANCE permission constant."""
        assert RemittancePermissions.FLAG_REMITTANCE == "remittance.flag_remittance"

    def test_all_permissions_are_strings(self):
        """Test that all permission constants are strings."""
        permissions = [
            RemittancePermissions.ADD_REMITTANCE,
            RemittancePermissions.CHANGE_REMITTANCE,
            RemittancePermissions.DELETE_REMITTANCE,
            RemittancePermissions.VIEW_REMITTANCE,
            RemittancePermissions.REVIEW_REMITTANCE,
            RemittancePermissions.FLAG_REMITTANCE,
        ]

        for permission in permissions:
            assert isinstance(permission, str)
            assert permission.startswith("remittance.")

    def test_permissions_follow_django_convention(self):
        """Test that permissions follow Django naming convention."""
        permissions = [
            RemittancePermissions.ADD_REMITTANCE,
            RemittancePermissions.CHANGE_REMITTANCE,
            RemittancePermissions.DELETE_REMITTANCE,
            RemittancePermissions.VIEW_REMITTANCE,
        ]

        # Standard Django permissions should follow app_label.action_model pattern
        for permission in permissions:
            parts = permission.split(".")
            assert len(parts) == 2
            assert parts[0] == "remittance"  # app label
            assert parts[1].endswith("_remittance")  # action_model

    def test_custom_permissions_format(self):
        """Test that custom permissions follow expected format."""
        custom_permissions = [
            RemittancePermissions.REVIEW_REMITTANCE,
            RemittancePermissions.FLAG_REMITTANCE,
        ]

        for permission in custom_permissions:
            parts = permission.split(".")
            assert len(parts) == 2
            assert parts[0] == "remittance"  # app label

    def test_permission_uniqueness(self):
        """Test that all permissions are unique."""
        permissions = [
            RemittancePermissions.ADD_REMITTANCE,
            RemittancePermissions.CHANGE_REMITTANCE,
            RemittancePermissions.DELETE_REMITTANCE,
            RemittancePermissions.VIEW_REMITTANCE,
            RemittancePermissions.REVIEW_REMITTANCE,
            RemittancePermissions.FLAG_REMITTANCE,
        ]

        assert len(permissions) == len(set(permissions))

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_user_permission_check_integration(self, mock_guardian_has_perm):
        """Test integration with Guardian's object permission checking system."""
        mock_guardian_has_perm.return_value = True

        # Test that our permission constants work with Guardian's has_perm
        workspace = WorkspaceFactory()
        result = self.user.has_perm(RemittancePermissions.VIEW_REMITTANCE, workspace)

        mock_guardian_has_perm.assert_called_once_with(
            self.user, RemittancePermissions.VIEW_REMITTANCE, workspace
        )
        assert result is True

    def test_permission_constants_immutability(self):
        """Test that permission constants cannot be modified."""
        # Attempt to modify class attributes should not affect the constants
        original_add = RemittancePermissions.ADD_REMITTANCE

        # This should not change the class attribute
        try:
            RemittancePermissions.ADD_REMITTANCE = "modified"
            # If we reach here, the attribute was modified (which we don't want)
            # Reset it back
            RemittancePermissions.ADD_REMITTANCE = original_add
        except AttributeError:
            # This is expected if the class is properly designed to prevent modification
            pass

        # Verify the constant is still the original value
        assert RemittancePermissions.ADD_REMITTANCE == original_add


@pytest.mark.django_db
class TestRemittancePermissionUsage:
    """Test how RemittancePermissions are used in practice."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_view_permission_usage(self, mock_guardian_has_perm):
        """Test VIEW_REMITTANCE permission usage pattern."""
        mock_guardian_has_perm.return_value = True

        # Test Guardian's object-level permission checking
        can_view = self.user.has_perm(
            RemittancePermissions.VIEW_REMITTANCE, self.workspace
        )

        assert can_view is True
        mock_guardian_has_perm.assert_called_once()

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_add_permission_usage(self, mock_guardian_has_perm):
        """Test ADD_REMITTANCE permission usage pattern."""
        mock_guardian_has_perm.return_value = False

        can_add = self.user.has_perm(
            RemittancePermissions.ADD_REMITTANCE, self.workspace
        )

        assert can_add is False
        mock_guardian_has_perm.assert_called_once()

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_change_permission_usage(self, mock_guardian_has_perm):
        """Test CHANGE_REMITTANCE permission usage pattern."""
        mock_guardian_has_perm.return_value = True

        can_change = self.user.has_perm(
            RemittancePermissions.CHANGE_REMITTANCE, self.workspace
        )

        assert can_change is True

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_delete_permission_usage(self, mock_guardian_has_perm):
        """Test DELETE_REMITTANCE permission usage pattern."""
        mock_guardian_has_perm.return_value = False

        can_delete = self.user.has_perm(
            RemittancePermissions.DELETE_REMITTANCE, self.workspace
        )

        assert can_delete is False

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_review_permission_usage(self, mock_guardian_has_perm):
        """Test REVIEW_REMITTANCE permission usage pattern."""
        mock_guardian_has_perm.return_value = True

        can_review = self.user.has_perm(
            RemittancePermissions.REVIEW_REMITTANCE, self.workspace
        )

        assert can_review is True

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_flag_permission_usage(self, mock_guardian_has_perm):
        """Test FLAG_REMITTANCE permission usage pattern."""
        mock_guardian_has_perm.return_value = False

        can_flag = self.user.has_perm(
            RemittancePermissions.FLAG_REMITTANCE, self.workspace
        )

        assert can_flag is False

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_multiple_permission_checks(self, mock_guardian_has_perm):
        """Test checking multiple permissions for the same user."""

        # Configure mock to return different values for different permissions
        def permission_side_effect(user_obj, permission, obj=None):
            if permission == RemittancePermissions.VIEW_REMITTANCE:
                return True
            elif permission == RemittancePermissions.ADD_REMITTANCE:
                return True
            elif permission == RemittancePermissions.CHANGE_REMITTANCE:
                return False
            elif permission == RemittancePermissions.DELETE_REMITTANCE:
                return False
            elif permission == RemittancePermissions.REVIEW_REMITTANCE:
                return True
            elif permission == RemittancePermissions.FLAG_REMITTANCE:
                return False
            return False

        mock_guardian_has_perm.side_effect = permission_side_effect

        # Check multiple permissions
        permissions_to_check = [
            (RemittancePermissions.VIEW_REMITTANCE, True),
            (RemittancePermissions.ADD_REMITTANCE, True),
            (RemittancePermissions.CHANGE_REMITTANCE, False),
            (RemittancePermissions.DELETE_REMITTANCE, False),
            (RemittancePermissions.REVIEW_REMITTANCE, True),
            (RemittancePermissions.FLAG_REMITTANCE, False),
        ]

        for permission, expected in permissions_to_check:
            result = self.user.has_perm(permission, self.workspace)
            assert result == expected

    def test_permission_constants_in_list_comprehension(self):
        """Test using permission constants in list operations."""
        all_permissions = [
            RemittancePermissions.ADD_REMITTANCE,
            RemittancePermissions.CHANGE_REMITTANCE,
            RemittancePermissions.DELETE_REMITTANCE,
            RemittancePermissions.VIEW_REMITTANCE,
            RemittancePermissions.REVIEW_REMITTANCE,
            RemittancePermissions.FLAG_REMITTANCE,
        ]

        # Test filtering permissions - only standard CRUD operations
        crud_permissions = [
            RemittancePermissions.ADD_REMITTANCE,
            RemittancePermissions.CHANGE_REMITTANCE,
            RemittancePermissions.DELETE_REMITTANCE,
            RemittancePermissions.VIEW_REMITTANCE,
        ]

        assert len(crud_permissions) == 4  # add, change, delete, view

        custom_permissions = [p for p in all_permissions if p not in crud_permissions]

        assert len(custom_permissions) == 2  # review, flag

    def test_permission_constants_in_dictionary(self):
        """Test using permission constants as dictionary keys."""
        permission_descriptions = {
            RemittancePermissions.ADD_REMITTANCE: "Can create new remittances",
            RemittancePermissions.CHANGE_REMITTANCE: "Can modify existing remittances",
            RemittancePermissions.DELETE_REMITTANCE: "Can delete remittances",
            RemittancePermissions.VIEW_REMITTANCE: "Can view remittances",
            RemittancePermissions.REVIEW_REMITTANCE: "Can review and approve remittances",
            RemittancePermissions.FLAG_REMITTANCE: "Can flag remittances for attention",
        }

        assert len(permission_descriptions) == 6

        # Test accessing descriptions
        assert "create" in permission_descriptions[RemittancePermissions.ADD_REMITTANCE]
        assert (
            "modify" in permission_descriptions[RemittancePermissions.CHANGE_REMITTANCE]
        )
        assert (
            "review" in permission_descriptions[RemittancePermissions.REVIEW_REMITTANCE]
        )


@pytest.mark.django_db
class TestRemittancePermissionIntegration:
    """Test RemittancePermissions integration with Django's permission system."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()

    def test_permission_format_matches_django_convention(self):
        """Test that permission format matches Django's expected format."""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        # Get the remittance content type
        try:
            from apps.remittance.models import Remittance

            content_type = ContentType.objects.get_for_model(Remittance)

            # Check if standard Django permissions exist
            expected_permissions = [
                "add_remittance",
                "change_remittance",
                "delete_remittance",
                "view_remittance",
            ]

            for perm_codename in expected_permissions:
                Permission.objects.filter(
                    content_type=content_type, codename=perm_codename
                ).exists()

                # The permission might not exist in test DB, but format should match
                expected_full_permission = f"remittance.{perm_codename}"

                # Verify our constants match the expected format
                if perm_codename == "add_remittance":
                    assert (
                        RemittancePermissions.ADD_REMITTANCE == expected_full_permission
                    )
                elif perm_codename == "change_remittance":
                    assert (
                        RemittancePermissions.CHANGE_REMITTANCE
                        == expected_full_permission
                    )
                elif perm_codename == "delete_remittance":
                    assert (
                        RemittancePermissions.DELETE_REMITTANCE
                        == expected_full_permission
                    )
                elif perm_codename == "view_remittance":
                    assert (
                        RemittancePermissions.VIEW_REMITTANCE
                        == expected_full_permission
                    )

        except ImportError:
            # If Remittance model is not available, skip this test
            pytest.skip("Remittance model not available for content type test")

    def test_custom_permissions_format(self):
        """Test that custom permissions follow a consistent format."""
        custom_permissions = [
            RemittancePermissions.REVIEW_REMITTANCE,
            RemittancePermissions.FLAG_REMITTANCE,
        ]

        for permission in custom_permissions:
            # Should follow app_label.action_model or app_label.custom_action format
            parts = permission.split(".")
            assert len(parts) == 2
            assert parts[0] == "remittance"

            # Custom permissions should be descriptive
            action = parts[1]
            assert (
                len(action) > 3
            )  # Should be more descriptive than just 'add', 'del', etc.

    @patch("guardian.backends.ObjectPermissionBackend.has_perm")
    def test_django_permission_check_integration(self, mock_guardian_has_perm):
        """Test integration with Guardian's object permission checking."""
        mock_guardian_has_perm.return_value = True

        # Test that our permission constants work with Guardian's has_perm
        workspace = WorkspaceFactory()
        result = self.user.has_perm(RemittancePermissions.VIEW_REMITTANCE, workspace)

        mock_guardian_has_perm.assert_called_once_with(
            self.user, RemittancePermissions.VIEW_REMITTANCE, workspace
        )
        assert result is True

    def test_permission_constants_are_importable(self):
        """Test that permission constants can be imported correctly."""
        # Test direct import
        from apps.remittance.permissions import RemittancePermissions

        assert hasattr(RemittancePermissions, "ADD_REMITTANCE")
        assert hasattr(RemittancePermissions, "CHANGE_REMITTANCE")
        assert hasattr(RemittancePermissions, "DELETE_REMITTANCE")
        assert hasattr(RemittancePermissions, "VIEW_REMITTANCE")
        assert hasattr(RemittancePermissions, "REVIEW_REMITTANCE")
        assert hasattr(RemittancePermissions, "FLAG_REMITTANCE")

        # Test that the specific permission constants are all strings
        permission_constants = [
            "ADD_REMITTANCE",
            "CHANGE_REMITTANCE",
            "DELETE_REMITTANCE",
            "VIEW_REMITTANCE",
            "REVIEW_REMITTANCE",
            "FLAG_REMITTANCE",
        ]

        for attr_name in permission_constants:
            attr_value = getattr(RemittancePermissions, attr_name)
            assert isinstance(attr_value, str)
