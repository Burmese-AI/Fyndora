"""
Unit tests for Entry service business logic.

Tests entry_create service function validation and business rules.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from apps.auditlog.models import AuditTrail
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

    def test_entry_create_creates_audit_trail_entry(self):
        """Test that creating an entry also creates an audit trail record."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        entry = entry_create(
            submitted_by=submitter,
            entry_type="income",
            amount=Decimal("150.00"),
            description="Test entry for audit trail",
        )

        assert AuditTrail.objects.count() == 1
        audit_log = AuditTrail.objects.first()
        assert audit_log.user == submitter.organization_member.user
        assert audit_log.action_type == "entry_created"
        assert audit_log.target_entity == entry.entry_id
        assert audit_log.target_entity_type == "entry"
        assert audit_log.metadata == {
            "entry_type": "income",
            "amount": "150.00",
            "description": "Test entry for audit trail",
        }
