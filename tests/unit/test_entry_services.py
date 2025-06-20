"""
Unit tests for Entry service business logic.

Tests entry_create service function validation and business rules.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.entries.services import entry_create
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    TeamMemberFactory, 
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryCreateService:
    """Test entry_create service business logic."""
    
    def setup_method(self, method):
        """Set up test data."""
        self.submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        self.workspace = WorkspaceFactory(organization=self.submitter.organization_member.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, 
            team=self.submitter.team
        )

    def test_entry_create_with_valid_submitter(self):
        """Test entry creation with valid submitter role."""
        entry = entry_create(
            submitted_by=self.submitter,
            entry_type="income",
            amount=Decimal("100.00"),
            description="Test donation",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert entry.submitter == self.submitter
        assert entry.entry_type == "income"
        assert entry.amount == Decimal("100.00")
        assert entry.description == "Test donation"
        assert entry.status == "pending_review"  # Default status

    def test_entry_create_fails_with_invalid_submitter_role(self):
        """Test entry creation fails with non-submitter role."""
        auditor = TeamMemberFactory(role=TeamMemberRole.AUDITOR)

        with pytest.raises(ValueError) as exc_info:
            entry_create(
                submitted_by=auditor,
                entry_type="income",
                amount=Decimal("100.00"),
                description="Test donation",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
            )

        assert "Only users with Submitter role can create entries." in str(
            exc_info.value
        )

    def test_entry_create_fails_with_zero_amount(self):
        """Test entry creation fails with zero amount."""
        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=self.submitter,
                entry_type="income",
                amount=Decimal("0.00"),
                description="Test donation",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
            )

        assert "Amount must be greater than zero." in str(exc_info.value)

    def test_entry_create_fails_with_negative_amount(self):
        """Test entry creation fails with negative amount."""
        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=self.submitter,
                entry_type="income",
                amount=Decimal("-50.00"),
                description="Test donation",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
            )

        assert "Amount must be greater than zero." in str(exc_info.value)

    def test_entry_create_with_different_entry_types(self):
        """Test entry creation with different entry types."""
        entry_types = ["income", "disbursement", "remittance"]

        for entry_type in entry_types:
            entry = entry_create(
                submitted_by=self.submitter,
                entry_type=entry_type,
                amount=Decimal("100.00"),
                description=f"Test {entry_type}",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
            )

            assert entry.entry_type == entry_type
            assert entry.description == f"Test {entry_type}"

    def test_entry_create_with_large_amount(self):
        """Test entry creation with large amount within limits."""
        # Large amount within max_digits=10, decimal_places=2 limit
        large_amount = Decimal("99999999.99")

        entry = entry_create(
            submitted_by=self.submitter,
            entry_type="income",
            amount=large_amount,
            description="Large donation",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert entry.amount == large_amount

    def test_entry_create_with_small_positive_amount(self):
        """Test entry creation with smallest positive amount."""
        entry = entry_create(
            submitted_by=self.submitter,
            entry_type="disbursement",
            amount=Decimal('0.01'),
            description="Small expense",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert entry.amount == Decimal('0.01')

    def test_entry_create_with_long_description(self):
        """Test entry creation with maximum length description."""
        # Max length is 255 characters
        long_description = "x" * 255

        entry = entry_create(
            submitted_by=self.submitter,
            entry_type="income",
            amount=Decimal("100.00"),
            description=long_description,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert entry.description == long_description
        assert len(entry.description) == 255

    @patch("apps.entries.services.audit_create")
    def test_entry_create_calls_audit_service(self, mock_audit_create):
        """Test that entry_create calls audit service with correct params."""
        entry = entry_create(
            submitted_by=self.submitter,
            entry_type="income",
            amount=Decimal("150.00"),
            description="Test entry",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # Verify audit_create was called with expected params
        mock_audit_create.assert_called_once_with(
            user=self.submitter.organization_member.user,
            action_type="entry_created",
            target_entity=entry,
            metadata={
                "entry_type": "income",
                "amount": "150.00",
                "description": "Test entry",
            },
        )
