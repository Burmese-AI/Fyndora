"""
Unit tests for apps.core.utils
"""

import pytest
from unittest.mock import Mock
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group

from apps.core.utils import (
    percent_change,
    round_decimal,
    get_paginated_context,
    model_update,
    can_manage_organization,
    revoke_workspace_admin_permission,
    revoke_operations_reviewer_permission,
    revoke_team_coordinator_permission,
    revoke_workspace_team_member_permission,
    check_if_member_is_owner,
)
from apps.core.permissions import OrganizationPermissions
from tests.factories import (
    CustomUserFactory,
    OrganizationFactory,
    WorkspaceFactory,
    TeamFactory,
    WorkspaceTeamFactory,
    OrganizationMemberFactory,
)


@pytest.mark.unit
class TestPercentChange:
    """Test percent_change utility function."""

    def test_percent_change_positive_change(self):
        """Test percent change with positive change."""
        result = percent_change(120.0, 100.0)
        assert result == "+20.0% from last period"

    def test_percent_change_negative_change(self):
        """Test percent change with negative change."""
        result = percent_change(80.0, 100.0)
        assert result == "-20.0% from last period"

    def test_percent_change_no_change(self):
        """Test percent change with no change."""
        result = percent_change(100.0, 100.0)
        assert result == "+0.0% from last period"

    def test_percent_change_previous_zero(self):
        """Test percent change when previous value is zero."""
        result = percent_change(100.0, 0.0)
        assert result == "0% change"

    def test_percent_change_current_zero(self):
        """Test percent change when current value is zero."""
        result = percent_change(0.0, 100.0)
        assert result == "-100.0% from last period"

    def test_percent_change_both_zero(self):
        """Test percent change when both values are zero."""
        result = percent_change(0.0, 0.0)
        assert result == "0% change"

    def test_percent_change_large_numbers(self):
        """Test percent change with large numbers."""
        result = percent_change(1000000.0, 500000.0)
        assert result == "+100.0% from last period"

    def test_percent_change_small_numbers(self):
        """Test percent change with small numbers."""
        result = percent_change(0.1, 0.05)
        assert result == "+100.0% from last period"

    def test_percent_change_decimal_precision(self):
        """Test percent change with decimal precision."""
        result = percent_change(33.33, 25.0)
        assert result == "+33.3% from last period"

    def test_percent_change_negative_previous(self):
        """Test percent change with negative previous value."""
        result = percent_change(50.0, -25.0)
        assert result == "-300.0% from last period"

    def test_percent_change_negative_current(self):
        """Test percent change with negative current value."""
        result = percent_change(-25.0, 50.0)
        assert result == "-150.0% from last period"

    def test_percent_change_both_negative(self):
        """Test percent change with both values negative."""
        result = percent_change(-30.0, -50.0)
        assert result == "-40.0% from last period"


@pytest.mark.unit
class TestRoundDecimal:
    """Test round_decimal utility function."""

    def test_round_decimal_default_places(self):
        """Test rounding with default 2 decimal places."""
        result = round_decimal(3.14159)
        assert result == 3.14

    def test_round_decimal_custom_places(self):
        """Test rounding with custom decimal places."""
        result = round_decimal(3.14159, places=3)
        assert result == 3.14

    def test_round_decimal_round_half_up(self):
        """Test rounding with ROUND_HALF_UP behavior."""
        result = round_decimal(2.5, places=0)
        assert result == 2.5

    def test_round_decimal_round_half_up_negative(self):
        """Test rounding with ROUND_HALF_UP behavior for negative numbers."""
        result = round_decimal(-2.5, places=0)
        assert result == -2.5

    def test_round_decimal_string_input(self):
        """Test rounding with string input."""
        result = round_decimal("3.14159")
        assert result == 3.14

    def test_round_decimal_integer_input(self):
        """Test rounding with integer input."""
        result = round_decimal(5)
        assert result == 5.0

    def test_round_decimal_zero(self):
        """Test rounding with zero."""
        result = round_decimal(0)
        assert result == 0.0

    def test_round_decimal_negative(self):
        """Test rounding with negative number."""
        result = round_decimal(-3.14159)
        assert result == -3.14

    def test_round_decimal_large_number(self):
        """Test rounding with large number."""
        result = round_decimal(1234567.891234, places=1)
        assert result == 1234567.89

    def test_round_decimal_small_number(self):
        """Test rounding with very small number."""
        result = round_decimal(0.000123456, places=4)
        assert result == 0.0


@pytest.mark.unit
class TestGetPaginatedContext:
    """Test get_paginated_context utility function."""

    def test_get_paginated_context_basic(self):
        """Test basic pagination context creation."""
        queryset = [1, 2, 3, 4, 5]
        context = {}

        result = get_paginated_context(
            queryset=queryset, context=context, object_name="items"
        )

        assert "page_obj" in result
        assert "paginator" in result
        assert "items" in result
        assert "is_paginated" in result
        assert result["items"] == [1, 2, 3, 4, 5]
        assert result["is_paginated"] is False

    def test_get_paginated_context_with_existing_context(self):
        """Test pagination context with existing context data."""
        queryset = [1, 2, 3]
        context = {"existing_key": "existing_value"}

        result = get_paginated_context(
            queryset=queryset, context=context, object_name="items"
        )

        assert result["existing_key"] == "existing_value"
        assert "items" in result
        assert result["items"] == [1, 2, 3]

    def test_get_paginated_context_custom_page_size(self):
        """Test pagination context with custom page size."""
        queryset = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        result = get_paginated_context(
            queryset=queryset, context={}, object_name="items", page_size=3
        )

        assert len(result["items"]) == 3
        assert result["items"] == [1, 2, 3]
        assert result["is_paginated"] is True

    def test_get_paginated_context_custom_page_number(self):
        """Test pagination context with custom page number."""
        queryset = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        result = get_paginated_context(
            queryset=queryset, context={}, object_name="items", page_size=3, page_no=2
        )

        assert result["items"] == [4, 5, 6]

    def test_get_paginated_context_empty_queryset(self):
        """Test pagination context with empty queryset."""
        queryset = []

        result = get_paginated_context(
            queryset=queryset, context={}, object_name="items"
        )

        assert result["items"] == []
        assert result["is_paginated"] is False

    def test_get_paginated_context_single_item(self):
        """Test pagination context with single item."""
        queryset = [1]

        result = get_paginated_context(
            queryset=queryset, context={}, object_name="items"
        )

        assert result["items"] == [1]
        assert result["is_paginated"] is False

    def test_get_paginated_context_large_queryset(self):
        """Test pagination context with large queryset."""
        queryset = list(range(1, 101))  # 100 items

        result = get_paginated_context(
            queryset=queryset, context={}, object_name="items", page_size=10
        )

        assert len(result["items"]) == 10
        assert result["items"] == list(range(1, 11))
        assert result["is_paginated"] is True

    def test_get_paginated_context_invalid_page_number(self):
        """Test pagination context with invalid page number."""
        queryset = [1, 2, 3, 4, 5]

        result = get_paginated_context(
            queryset=queryset,
            context={},
            object_name="items",
            page_size=2,
            page_no=999,  # Invalid page number
        )

        # Should return the last page
        assert result["items"] == [5]

    def test_get_paginated_context_zero_page_number(self):
        """Test pagination context with zero page number."""
        queryset = [1, 2, 3, 4, 5]

        result = get_paginated_context(
            queryset=queryset, context={}, object_name="items", page_size=2, page_no=0
        )

        # Should return the last page (Django paginator behavior)
        assert result["items"] == [5]


@pytest.mark.unit
class TestModelUpdate:
    """Test model_update utility function."""

    def test_model_update_basic(self):
        """Test basic model update functionality."""
        mock_instance = Mock()
        mock_instance.full_clean = Mock()
        mock_instance.save = Mock()

        data = {"name": "New Name", "email": "new@example.com"}

        result = model_update(mock_instance, data)

        assert result == mock_instance
        assert mock_instance.name == "New Name"
        assert mock_instance.email == "new@example.com"
        mock_instance.full_clean.assert_called_once()
        mock_instance.save.assert_called_once_with(update_fields=None)

    def test_model_update_with_update_fields(self):
        """Test model update with specific update fields."""
        mock_instance = Mock()
        mock_instance.full_clean = Mock()
        mock_instance.save = Mock()

        data = {"name": "New Name", "email": "new@example.com"}
        update_fields = ["name"]

        result = model_update(mock_instance, data, update_fields)

        assert result == mock_instance
        assert mock_instance.name == "New Name"
        assert mock_instance.email == "new@example.com"
        mock_instance.full_clean.assert_called_once()
        mock_instance.save.assert_called_once_with(update_fields=["name"])

    def test_model_update_validation_error(self):
        """Test model update with validation error."""
        mock_instance = Mock()
        mock_instance.full_clean = Mock(side_effect=ValidationError("Invalid data"))
        mock_instance.save = Mock()

        data = {"name": "Invalid Name"}

        with pytest.raises(ValidationError, match="Invalid data"):
            model_update(mock_instance, data)

        mock_instance.full_clean.assert_called_once()
        mock_instance.save.assert_not_called()


@pytest.mark.unit
class TestCanManageOrganization:
    """Test can_manage_organization utility function."""

    def test_can_manage_organization_with_permission(self):
        """Test can_manage_organization when user has permission."""
        user = Mock()
        organization = Mock()
        user.has_perm = Mock(return_value=True)

        result = can_manage_organization(user, organization)

        assert result is True
        user.has_perm.assert_called_once_with(
            OrganizationPermissions.MANAGE_ORGANIZATION, organization
        )

    def test_can_manage_organization_without_permission(self):
        """Test can_manage_organization when user lacks permission."""
        user = Mock()
        organization = Mock()
        user.has_perm = Mock(return_value=False)

        result = can_manage_organization(user, organization)

        assert result is False
        user.has_perm.assert_called_once_with(
            OrganizationPermissions.MANAGE_ORGANIZATION, organization
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestRevokeWorkspaceAdminPermission:
    """Test revoke_workspace_admin_permission utility function."""

    def test_revoke_workspace_admin_permission_existing_group(self):
        """Test revoking permission from existing group."""
        user = CustomUserFactory()
        workspace = WorkspaceFactory()
        group_name = f"Workspace Admins - {workspace.workspace_id}"

        # Create group and add user
        group = Group.objects.create(name=group_name)
        group.user_set.add(user)

        # Verify user is in group
        assert user in group.user_set.all()

        # Revoke permission
        revoke_workspace_admin_permission(user, workspace)

        # Verify user is removed from group
        group.refresh_from_db()
        assert user not in group.user_set.all()

    def test_revoke_workspace_admin_permission_new_group(self):
        """Test revoking permission when group doesn't exist."""
        user = CustomUserFactory()
        workspace = WorkspaceFactory()
        group_name = f"Workspace Admins - {workspace.workspace_id}"

        # Verify group doesn't exist
        assert not Group.objects.filter(name=group_name).exists()

        # Revoke permission (should create group but not add user)
        revoke_workspace_admin_permission(user, workspace)

        # Verify group was created
        group = Group.objects.get(name=group_name)
        assert user not in group.user_set.all()


@pytest.mark.unit
@pytest.mark.django_db
class TestRevokeOperationsReviewerPermission:
    """Test revoke_operations_reviewer_permission utility function."""

    def test_revoke_operations_reviewer_permission_existing_group(self):
        """Test revoking permission from existing group."""
        user = CustomUserFactory()
        workspace = WorkspaceFactory()
        group_name = f"Operations Reviewer - {workspace.workspace_id}"

        # Create group and add user
        group = Group.objects.create(name=group_name)
        group.user_set.add(user)

        # Verify user is in group
        assert user in group.user_set.all()

        # Revoke permission
        revoke_operations_reviewer_permission(user, workspace)

        # Verify user is removed from group
        group.refresh_from_db()
        assert user not in group.user_set.all()


@pytest.mark.unit
@pytest.mark.django_db
class TestRevokeTeamCoordinatorPermission:
    """Test revoke_team_coordinator_permission utility function."""

    def test_revoke_team_coordinator_permission_existing_group(self):
        """Test revoking permission from existing group."""
        user = CustomUserFactory()
        team = TeamFactory()
        group_name = f"Team Coordinator - {team.team_id}"

        # Create group and add user
        group = Group.objects.create(name=group_name)
        group.user_set.add(user)

        # Verify user is in group
        assert user in group.user_set.all()

        # Revoke permission
        revoke_team_coordinator_permission(user, team)

        # Verify user is removed from group
        group.refresh_from_db()
        assert user not in group.user_set.all()


@pytest.mark.unit
@pytest.mark.django_db
class TestRevokeWorkspaceTeamMemberPermission:
    """Test revoke_workspace_team_member_permission utility function."""

    def test_revoke_workspace_team_member_permission_existing_group(self):
        """Test revoking permission from existing group."""
        user = CustomUserFactory()
        workspace_team = WorkspaceTeamFactory()
        group_name = f"Workspace Team - {workspace_team.workspace_team_id}"

        # Create group and add user
        group = Group.objects.create(name=group_name)
        group.user_set.add(user)

        # Verify user is in group
        assert user in group.user_set.all()

        # Revoke permission
        revoke_workspace_team_member_permission(user, workspace_team)

        # Verify user is removed from group
        group.refresh_from_db()
        assert user not in group.user_set.all()


@pytest.mark.unit
@pytest.mark.django_db
class TestCheckIfMemberIsOwner:
    """Test check_if_member_is_owner utility function."""

    def test_check_if_member_is_owner_true(self):
        """Test when member is the owner."""
        organization = OrganizationFactory()
        owner_member = OrganizationMemberFactory(organization=organization)
        organization.owner = owner_member
        organization.save()

        result = check_if_member_is_owner(owner_member, organization)

        assert result is True

    def test_check_if_member_is_owner_false(self):
        """Test when member is not the owner."""
        organization = OrganizationFactory()
        owner_member = OrganizationMemberFactory(organization=organization)
        other_member = OrganizationMemberFactory(organization=organization)
        organization.owner = owner_member
        organization.save()

        result = check_if_member_is_owner(other_member, organization)

        assert result is False

    def test_check_if_member_is_owner_no_owner(self):
        """Test when organization has no owner."""
        organization = OrganizationFactory()
        organization.owner = None
        organization.save()
        member = OrganizationMemberFactory(organization=organization)

        result = check_if_member_is_owner(member, organization)

        assert result is False
