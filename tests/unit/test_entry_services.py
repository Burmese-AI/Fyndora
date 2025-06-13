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
from tests.factories import TeamMemberFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryCreateService:
    """Test entry_create service business logic."""

    def test_entry_create_with_valid_submitter(self):
        """Test entry creation with valid submitter role."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        entry = entry_create(
            submitted_by=submitter,
            entry_type="income",
            amount=Decimal("100.00"),
            description="Test donation",
        )

        assert entry.submitted_by == submitter
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
            )

        assert "Only users with Submitter role can create entries." in str(
            exc_info.value
        )

    def test_entry_create_fails_with_zero_amount(self):
        """Test entry creation fails with zero amount."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=submitter,
                entry_type="income",
                amount=Decimal("0.00"),
                description="Test donation",
            )

        assert "Amount must be greater than zero." in str(exc_info.value)

    def test_entry_create_fails_with_negative_amount(self):
        """Test entry creation fails with negative amount."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=submitter,
                entry_type="income",
                amount=Decimal("-50.00"),
                description="Test donation",
            )

        assert "Amount must be greater than zero." in str(exc_info.value)

    def test_entry_create_with_different_entry_types(self):
        """Test entry creation with different entry types."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        entry_types = ["income", "disbursement", "remittance"]

        for entry_type in entry_types:
            entry = entry_create(
                submitted_by=submitter,
                entry_type=entry_type,
                amount=Decimal("100.00"),
                description=f"Test {entry_type}",
            )

            assert entry.entry_type == entry_type
            assert entry.description == f"Test {entry_type}"

    def test_entry_create_with_large_amount(self):
        """Test entry creation with large amount within limits."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Large amount within max_digits=10, decimal_places=2 limit
        large_amount = Decimal("99999999.99")

        entry = entry_create(
            submitted_by=submitter,
            entry_type="income",
            amount=large_amount,
            description="Large donation",
        )

        assert entry.amount == large_amount

    def test_entry_create_with_small_positive_amount(self):
        """Test entry creation with smallest positive amount."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        entry = entry_create(
            submitted_by=submitter,
            entry_type="disbursement",
            amount=Decimal("0.01"),
            description="Small expense",
        )

        assert entry.amount == Decimal("0.01")

    def test_entry_create_with_long_description(self):
        """Test entry creation with maximum length description."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Max length is 255 characters
        long_description = "x" * 255

        entry = entry_create(
            submitted_by=submitter,
            entry_type="income",
            amount=Decimal("100.00"),
            description=long_description,
        )

        assert entry.description == long_description
        assert len(entry.description) == 255

    @patch("apps.entries.services.audit_create")
    def test_entry_create_calls_audit_service(self, mock_audit_create):
        """Test that entry_create calls audit service with correct params."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        entry = entry_create(
            submitted_by=submitter,
            entry_type="income",
            amount=Decimal("150.00"),
            description="Test entry",
        )

        # Verify audit_create was called with expected params
        mock_audit_create.assert_called_once_with(
            user=submitter.organization_member.user,
            action_type="entry_created",
            target_entity=entry.entry_id,
            target_entity_type="entry",
            metadata={
                "entry_type": "income",
                "amount": "150.00",
                "description": "Test entry",
            },
        )
