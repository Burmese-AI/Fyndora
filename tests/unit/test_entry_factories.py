"""
Unit tests for Entry factories.
"""

import pytest
from decimal import Decimal

from apps.entries.models import Entry
from apps.entries.constants import ENTRY_TYPE_CHOICES
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    EntryFactory,
    IncomeEntryFactory,
    DisbursementEntryFactory,
    RemittanceEntryFactory,
    PendingEntryFactory,
    ApprovedEntryFactory,
    RejectedEntryFactory,
    FlaggedEntryFactory,
    LargeAmountEntryFactory,
    SmallAmountEntryFactory,
    EntryWithReviewFactory,
)


@pytest.mark.django_db
class TestEntryFactories:
    """Test entry-related factories."""

    def test_entry_factory_creates_valid_entry(self):
        """Test EntryFactory creates a valid entry."""
        entry = EntryFactory()

        assert isinstance(entry, Entry)
        assert entry.entry_id is not None
        assert entry.submitted_by is not None
        assert entry.submitted_by.role == TeamMemberRole.SUBMITTER
        assert entry.entry_type in [choice[0] for choice in ENTRY_TYPE_CHOICES]
        assert entry.amount > 0
        assert entry.description is not None
        assert entry.status == "pending_review"
        assert entry.reviewed_by is None
        assert entry.review_notes is None

    def test_income_entry_factory(self):
        """Test IncomeEntryFactory creates income entry."""
        entry = IncomeEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.entry_type == "income"
        assert entry.description.startswith("Donation collection from supporters batch")

    def test_disbursement_entry_factory(self):
        """Test DisbursementEntryFactory creates disbursement entry."""
        entry = DisbursementEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.entry_type == "disbursement"
        assert entry.description.startswith("Campaign expense payment")

    def test_remittance_entry_factory(self):
        """Test RemittanceEntryFactory creates remittance entry."""
        entry = RemittanceEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.entry_type == "remittance"
        assert entry.description.startswith("Remittance payment to central platform")


@pytest.mark.django_db
class TestEntryStatusFactories:
    """Test entry factories with different statuses."""

    def test_pending_entry_factory(self):
        """Test PendingEntryFactory creates pending entry."""
        entry = PendingEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.status == "pending_review"
        assert entry.description.startswith("Financial transaction awaiting review")
        assert entry.reviewed_by is None
        assert entry.review_notes is None

    def test_approved_entry_factory(self):
        """Test ApprovedEntryFactory creates approved entry."""
        entry = ApprovedEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.status == "approved"
        assert entry.description.startswith("Approved financial transaction")
        assert entry.reviewed_by is not None
        assert entry.reviewed_by.role == TeamMemberRole.TEAM_COORDINATOR
        assert entry.review_notes is not None

    def test_rejected_entry_factory(self):
        """Test RejectedEntryFactory creates rejected entry."""
        entry = RejectedEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.status == "rejected"
        assert entry.description.startswith("Rejected financial transaction")
        assert entry.reviewed_by is not None
        assert entry.reviewed_by.role == TeamMemberRole.OPERATIONS_REVIEWER
        assert entry.review_notes is not None

    def test_flagged_entry_factory(self):
        """Test FlaggedEntryFactory creates flagged entry."""
        entry = FlaggedEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.status == "flagged"
        assert entry.description.startswith("Flagged financial transaction")
        assert entry.reviewed_by is not None
        assert entry.reviewed_by.role == TeamMemberRole.WORKSPACE_ADMIN
        assert entry.review_notes is not None


@pytest.mark.django_db
class TestEntryAmountFactories:
    """Test entry factories with specific amounts."""

    def test_large_amount_entry_factory(self):
        """Test LargeAmountEntryFactory creates large amount entry."""
        entry = LargeAmountEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.amount == Decimal("25000.00")
        assert entry.entry_type == "income"
        assert entry.description.startswith("Major donation from corporate sponsor")

    def test_small_amount_entry_factory(self):
        """Test SmallAmountEntryFactory creates small amount entry."""
        entry = SmallAmountEntryFactory()

        assert isinstance(entry, Entry)
        assert entry.amount == Decimal("50.00")
        assert entry.entry_type == "disbursement"
        assert entry.description.startswith("Small campaign expense")


@pytest.mark.django_db
class TestEntryWithReviewFactory:
    """Test entry factory with review functionality."""

    def test_entry_with_review_factory_default(self):
        """Test EntryWithReviewFactory creates approved entry by default."""
        entry = EntryWithReviewFactory()

        assert isinstance(entry, Entry)
        assert entry.status == "approved"
        assert entry.reviewed_by is not None
        assert entry.review_notes is not None
        assert "approved" in entry.review_notes.lower()

    def test_entry_with_review_factory_custom_status(self):
        """Test EntryWithReviewFactory with custom status."""
        entry = EntryWithReviewFactory(review="rejected")

        assert isinstance(entry, Entry)
        assert entry.status == "rejected"
        assert entry.reviewed_by is not None
        assert entry.review_notes is not None
        assert "rejected" in entry.review_notes.lower()

    def test_entry_with_review_factory_flagged(self):
        """Test EntryWithReviewFactory with flagged status."""
        entry = EntryWithReviewFactory(review="flagged")

        assert isinstance(entry, Entry)
        assert entry.status == "flagged"
        assert entry.reviewed_by is not None
        assert entry.review_notes is not None
        assert "flagged" in entry.review_notes.lower()


@pytest.mark.django_db
class TestEntryValidation:
    """Test entry validation through factories."""

    def test_entry_submitter_role_validation(self):
        """Test that entries can only be submitted by submitters."""
        entry = EntryFactory()

        # Should be created with submitter role
        assert entry.submitted_by.role == TeamMemberRole.SUBMITTER

        # Entry should be valid
        entry.full_clean()  # Should not raise validation error

    def test_entry_reviewer_role_validation(self):
        """Test that entries can only be reviewed by authorized roles."""
        approved_entry = ApprovedEntryFactory()

        # Should be reviewed by authorized role
        assert approved_entry.reviewed_by.role in [
            TeamMemberRole.WORKSPACE_ADMIN,
            TeamMemberRole.OPERATIONS_REVIEWER,
            TeamMemberRole.TEAM_COORDINATOR,
        ]

        # Entry should be valid
        approved_entry.full_clean()  # Should not raise validation error
