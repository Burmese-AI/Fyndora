"""
Unit tests for core utility functions.

Tests model_update utility function validation and update behavior.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.utils import model_update
from apps.entries.models import Entry
from tests.factories import EntryFactory
from django.test import RequestFactory
from apps.core.utils import permission_denied_view
from django.http import HttpResponse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect
from tests.factories import CustomUserFactory, OrganizationMemberFactory



@pytest.mark.unit
@pytest.mark.django_db
#initially, ko swam used org models to test the decimal field by using the expense field of the org model.However , as we removed the expense field from the org model, we are using the entry model to test the decimal field.
class TestModelUpdateUtility:
    """Test model_update utility function."""

    def test_model_update_valid_data(self):
        """Test model_update with valid data."""
        # Use Entry model as it already exists with decimal fields
        test_model = EntryFactory(amount=Decimal("100.00"))

        updated_model = model_update(
            instance=test_model,
            data={
                "description": "Updated Description",
                "amount": Decimal("200.00"),
            },
            update_fields=["description", "amount"],
        )

        assert updated_model.description == "Updated Description"
        assert updated_model.amount == Decimal("200.00")

        # Verify it was saved
        updated_model.refresh_from_db()
        assert updated_model.description == "Updated Description"
        assert updated_model.amount == Decimal("200.00")

    def test_model_update_with_validation_error(self):
        """Test model_update with data that fails validation."""
        test_model = EntryFactory(amount=Decimal("100.00"))

        # Try to update with negative amount (should fail validation)
        with pytest.raises(ValidationError):
            model_update(
                instance=test_model,
                data={"amount": Decimal("-100.00")},
                update_fields=["amount"],
            )

    def test_model_update_without_update_fields(self):
        """Test model_update without specifying update_fields."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        updated_model = model_update(instance=test_model, data={"description": "Updated Description"})

        assert updated_model.description == "Updated Description"

        # Verify it was saved (all fields)
        updated_model.refresh_from_db()
        assert updated_model.description == "Updated Description"

    def test_model_update_partial_fields(self):
        """Test model_update with only specific fields."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        updated_model = model_update(
            instance=test_model,
            data={
                "description": "Updated Description",
                "amount": Decimal("200.00"),
            },
            update_fields=["description"],  # Only update description
        )

        assert updated_model.description == "Updated Description"
        assert updated_model.amount == Decimal("200.00")  # In memory

        # Verify only description was saved to database
        updated_model.refresh_from_db()
        assert updated_model.description == "Updated Description"
        # Note: Since we only updated description field, amount change may not persist
        # This depends on Django's update_fields behavior

    def test_model_update_empty_data(self):
        """Test model_update with empty data."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))
        original_description = test_model.description

        updated_model = model_update(instance=test_model, data={}, update_fields=[])

        # Should remain unchanged
        assert updated_model.description == original_description

        updated_model.refresh_from_db()
        assert updated_model.description == original_description

    def test_model_update_returns_instance(self):
        """Test that model_update returns the updated instance."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        result = model_update(
            instance=test_model, data={"description": "New Description"}, update_fields=["description"]
        )

        # Should return the same instance
        assert result is test_model
        assert result.description == "New Description"

    def test_model_update_calls_full_clean(self):
        """Test that model_update calls full_clean for validation."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        # This should trigger validation and fail
        with pytest.raises(ValidationError):
            model_update(
                instance=test_model,
                data={
                    "amount": Decimal("-50.00")
                },  # Negative amount fails validation
                update_fields=["amount"],
            )

        # Original instance should be unchanged since validation failed
        test_model.refresh_from_db()
        assert test_model.amount == Decimal("100.00")  # Original value

    def test_model_update_with_multiple_field_types(self):
        """Test model_update with different field types."""
        test_model = EntryFactory(description="Original Description", amount=Decimal("100.00"))

        updated_model = model_update(
            instance=test_model,
            data={
                "description": "New Description",
                "amount": Decimal("250.50"),
                "is_flagged": True,
            },
            update_fields=["description", "amount", "is_flagged"],
        )

        assert updated_model.description == "New Description"
        assert updated_model.amount == Decimal("250.50")
        assert updated_model.is_flagged == True

        # Verify persistence
        updated_model.refresh_from_db()
        assert updated_model.description == "New Description"
        assert updated_model.amount == Decimal("250.50")
        assert updated_model.is_flagged == True


@pytest.mark.unit
@pytest.mark.django_db
class TestCoreUtilityFunctions:
    """Test core utility functions."""

    def setup_method(self):
        """Set up test data."""
        from tests.factories import (
            CustomUserFactory, 
            OrganizationFactory, 
            OrganizationMemberFactory,
            WorkspaceFactory,
            TeamFactory,
            WorkspaceTeamFactory
        )
        from django.contrib.auth.models import Group
        from apps.core.permissions import OrganizationPermissions
        
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.organization_member = OrganizationMemberFactory(
            user=self.user,
            organization=self.organization
        )
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace,
            team=self.team
        )
        self.OrganizationPermissions = OrganizationPermissions
        self.Group = Group

    def test_can_manage_organization_with_permission(self):
        """Test can_manage_organization returns True when user has permission."""
        from apps.core.utils import can_manage_organization
        
        # Mock user.has_perm to return True
        self.user.has_perm = lambda perm, obj: True
        
        result = can_manage_organization(self.user, self.organization)
        assert result is True

    def test_can_manage_organization_without_permission(self):
        """Test can_manage_organization returns False when user lacks permission."""
        from apps.core.utils import can_manage_organization
        
        # Mock user.has_perm to return False
        self.user.has_perm = lambda perm, obj: False
        
        result = can_manage_organization(self.user, self.organization)
        assert result is False

    def test_can_manage_organization_calls_has_perm_with_correct_parameters(self):
        """Test can_manage_organization calls has_perm with correct permission and organization."""
        from apps.core.utils import can_manage_organization
        
        # Track calls to has_perm
        called_perms = []
        called_objs = []
        
        def mock_has_perm(perm, obj):
            called_perms.append(perm)
            called_objs.append(obj)
            return True
        
        self.user.has_perm = mock_has_perm
        
        can_manage_organization(self.user, self.organization)
        
        assert len(called_perms) == 1
        assert called_perms[0] == self.OrganizationPermissions.MANAGE_ORGANIZATION
        assert len(called_objs) == 1
        assert called_objs[0] == self.organization

    def test_revoke_workspace_admin_permission(self):
        """Test revoke_workspace_admin_permission removes user from workspace admin group."""
        from apps.core.utils import revoke_workspace_admin_permission
        
        # Create workspace admin group and add user
        group_name = f"Workspace Admins - {self.workspace.workspace_id}"
        group = self.Group.objects.create(name=group_name)
        group.user_set.add(self.user)
        
        # Verify user is in group
        assert self.user in group.user_set.all()
        
        # Revoke permission
        revoke_workspace_admin_permission(self.user, self.workspace)
        
        # Verify user is removed from group
        group.refresh_from_db()
        assert self.user not in group.user_set.all()

    def test_revoke_workspace_admin_permission_creates_group_if_not_exists(self):
        """Test revoke_workspace_admin_permission creates group if it doesn't exist."""
        from apps.core.utils import revoke_workspace_admin_permission
        
        group_name = f"Workspace Admins - {self.workspace.workspace_id}"
        
        # Verify group doesn't exist initially
        assert not self.Group.objects.filter(name=group_name).exists()
        
        # Revoke permission (should create group)
        revoke_workspace_admin_permission(self.user, self.workspace)
        
        # Verify group was created
        assert self.Group.objects.filter(name=group_name).exists()

    def test_revoke_operations_reviewer_permission(self):
        """Test revoke_operations_reviewer_permission removes user from operations reviewer group."""
        from apps.core.utils import revoke_operations_reviewer_permission
        
        # Create operations reviewer group and add user
        group_name = f"Operations Reviewer - {self.workspace.workspace_id}"
        group = self.Group.objects.create(name=group_name)
        group.user_set.add(self.user)
        
        # Verify user is in group
        assert self.user in group.user_set.all()
        
        # Revoke permission
        revoke_operations_reviewer_permission(self.user, self.workspace)
        
        # Verify user is removed from group
        group.refresh_from_db()
        assert self.user not in group.user_set.all()

    def test_revoke_team_coordinator_permission(self):
        """Test revoke_team_coordinator_permission removes user from team coordinator group."""
        from apps.core.utils import revoke_team_coordinator_permission
        
        # Create team coordinator group and add user
        group_name = f"Team Coordinator - {self.team.team_id}"
        group = self.Group.objects.create(name=group_name)
        group.user_set.add(self.user)
        
        # Verify user is in group
        assert self.user in group.user_set.all()
        
        # Revoke permission
        revoke_team_coordinator_permission(self.user, self.team)
        
        # Verify user is removed from group
        group.refresh_from_db()
        assert self.user not in group.user_set.all()

    def test_revoke_workspace_team_member_permission(self):
        """Test revoke_workspace_team_member_permission removes user from workspace team group."""
        from apps.core.utils import revoke_workspace_team_member_permission
        
        # Create workspace team group and add user
        group_name = f"Workspace Team - {self.workspace_team.workspace_team_id}"
        group = self.Group.objects.create(name=group_name)
        group.user_set.add(self.user)
        
        # Verify user is in group
        assert self.user in group.user_set.all()
        
        # Revoke permission
        revoke_workspace_team_member_permission(self.user, self.workspace_team)
        
        # Verify user is removed from group
        group.refresh_from_db()
        assert self.user not in group.user_set.all()

    def test_revoke_permissions_with_user_not_in_group(self):
        """Test revoke functions handle case where user is not in group gracefully."""
        from apps.core.utils import (
            revoke_workspace_admin_permission,
            revoke_operations_reviewer_permission,
            revoke_team_coordinator_permission,
            revoke_workspace_team_member_permission
        )
        
        # These should not raise errors even if user is not in group
        revoke_workspace_admin_permission(self.user, self.workspace)
        revoke_operations_reviewer_permission(self.user, self.workspace)
        revoke_team_coordinator_permission(self.user, self.team)
        revoke_workspace_team_member_permission(self.user, self.workspace_team)

    def test_check_if_member_is_owner_true(self):
        """Test check_if_member_is_owner returns True when member is organization owner."""
        from apps.core.utils import check_if_member_is_owner
        
        # Set the member as organization owner
        self.organization.owner = self.organization_member
        self.organization.save()
        
        result = check_if_member_is_owner(self.organization_member, self.organization)
        assert result is True

    def test_check_if_member_is_owner_false(self):
        """Test check_if_member_is_owner returns False when member is not organization owner."""
        from apps.core.utils import check_if_member_is_owner
        
        # Create another member who is not the owner
        other_member = OrganizationMemberFactory(organization=self.organization)
        
        result = check_if_member_is_owner(other_member, self.organization)
        assert result is False

    def test_check_if_member_is_owner_with_none_owner(self):
        """Test check_if_member_is_owner handles case where organization has no owner."""
        from apps.core.utils import check_if_member_is_owner
        
        # Ensure organization has no owner
        self.organization.owner = None
        self.organization.save()
        
        result = check_if_member_is_owner(self.organization_member, self.organization)
        assert result is False

    def test_check_if_member_is_owner_compares_user_objects(self):
        """Test check_if_member_is_owner correctly compares user objects."""
        from apps.core.utils import check_if_member_is_owner
        
        # Set the member as organization owner
        self.organization.owner = self.organization_member
        self.organization.save()
        
        # Create another member with different user but same organization
        other_user = CustomUserFactory()
        other_member = OrganizationMemberFactory(
            user=other_user,
            organization=self.organization
        )
        
        # Should return True for owner member
        assert check_if_member_is_owner(self.organization_member, self.organization) is True
        
        # Should return False for non-owner member
        assert check_if_member_is_owner(other_member, self.organization) is False






