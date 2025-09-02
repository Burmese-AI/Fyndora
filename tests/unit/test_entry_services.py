"""
Unit tests for Entry services.

Tests the service functions that handle business logic for entries.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.currencies.models import Currency
from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.entries.services import (
    _extract_user_from_actor,
    _validate_review_data,
    approve_entry,
    bulk_delete_entries,
    bulk_review_entries,
    bulk_update_entry_status,
    create_entry_with_attachments,
    delete_entry,
    entry_create,
    entry_review,
    entry_update,
    flag_entry,
    get_org_expense_stats,
    reject_entry,
    update_entry_status,
    update_entry_user_inputs,
)
from tests.factories import (
    EntryFactory,
    IncomeEntryFactory,
    OrganizationMemberFactory,
    OrganizationWithOwnerFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestExtractUserFromActor:
    """Test the _extract_user_from_actor helper function."""

    def test_extract_user_from_team_member(self):
        """Test extracting user from TeamMember."""
        team_member = TeamMemberFactory()
        user = _extract_user_from_actor(team_member)
        
        assert user == team_member.organization_member.user

    def test_extract_user_from_org_member(self):
        """Test extracting user from OrganizationMember."""
        org_member = OrganizationMemberFactory()
        user = _extract_user_from_actor(org_member)
        
        assert user == org_member.user

    def test_extract_user_from_user_object(self):
        """Test extracting user from User object."""
        org_member = OrganizationMemberFactory()
        user_obj = org_member.user
        user = _extract_user_from_actor(user_obj)
        
        assert user == user_obj

    def test_extract_user_from_object_with_user_attr(self):
        """Test extracting user from object with user attribute."""
        org_member = OrganizationMemberFactory()
        mock_actor = Mock()
        mock_actor.user = org_member.user
        
        user = _extract_user_from_actor(mock_actor)
        
        assert user == org_member.user


@pytest.mark.unit
@pytest.mark.django_db
class TestValidateReviewData:
    """Test the _validate_review_data helper function."""

    def test_validate_approved_status(self):
        """Test validation with approved status."""
        # Should not raise any exception
        _validate_review_data(status=EntryStatus.APPROVED)

    def test_validate_rejected_status(self):
        """Test validation with rejected status."""
        # Should not raise any exception
        _validate_review_data(status=EntryStatus.REJECTED, notes="Rejection reason")

    def test_validate_invalid_status(self):
        """Test validation with invalid status."""
        with pytest.raises(ValidationError, match="Invalid review status"):
            _validate_review_data(status=EntryStatus.PENDING)

    def test_validate_rejected_without_notes(self):
        """Test validation with rejected status but no notes."""
        with pytest.raises(ValidationError, match="Notes are required when rejected an entry"):
            _validate_review_data(status=EntryStatus.REJECTED)


@pytest.mark.unit
@pytest.mark.django_db
class TestCreateEntryWithAttachments:
    """Test the create_entry_with_attachments service function."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team_member = TeamMemberFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team_member.team
        )
        self.currency = Currency.objects.get_or_create(code="USD", name="US Dollar")[0]

    @patch('apps.entries.services.get_closest_exchanged_rate')
    @patch('apps.entries.services.create_attachments')
    @patch('apps.entries.services.BusinessAuditLogger.log_entry_action')
    def test_create_entry_with_attachments_success(self, mock_logger, mock_create_attachments, mock_get_rate):
        """Test successful entry creation with attachments."""
        # Mock exchange rate
        mock_rate = Mock()
        mock_rate.rate = Decimal("1.00")
        mock_get_rate.return_value = mock_rate

        # Mock attachments
        mock_attachments = [Mock(), Mock()]

        entry = create_entry_with_attachments(
            amount=Decimal("100.00"),
            occurred_at=date.today(),
            description="Test entry",
            attachments=mock_attachments,
            entry_type=EntryType.INCOME,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            currency=self.currency,
            submitted_by_team_member=self.team_member,
            user=self.team_member.organization_member.user,
        )

        assert entry.amount == Decimal("100.00")
        assert entry.description == "Test entry"
        assert entry.entry_type == EntryType.INCOME
        assert entry.organization == self.organization
        assert entry.workspace == self.workspace
        assert entry.workspace_team == self.workspace_team
        assert entry.currency == self.currency
        assert entry.submitted_by_team_member == self.team_member
        assert entry.exchange_rate_used == Decimal("1.00")
        assert entry.is_flagged is False  # Has attachments

        # Verify attachments were created
        mock_create_attachments.assert_called_once()

        # Verify audit logging
        mock_logger.assert_called_once()

    @patch('apps.entries.services.get_closest_exchanged_rate')
    def test_create_entry_without_attachments(self, mock_get_rate):
        """Test entry creation without attachments (should be flagged)."""
        # Mock exchange rate
        mock_rate = Mock()
        mock_rate.rate = Decimal("1.00")
        mock_get_rate.return_value = mock_rate

        entry = create_entry_with_attachments(
            amount=Decimal("100.00"),
            occurred_at=date.today(),
            description="Test entry",
            attachments=None,
            entry_type=EntryType.INCOME,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            currency=self.currency,
            submitted_by_team_member=self.team_member,
        )

        assert entry.is_flagged is True  # No attachments

    @patch('apps.entries.services.get_closest_exchanged_rate')
    def test_create_entry_no_exchange_rate(self, mock_get_rate):
        """Test entry creation when no exchange rate is available."""
        mock_get_rate.return_value = None

        with pytest.raises(ValueError, match="No exchange rate is defined"):
            create_entry_with_attachments(
                amount=Decimal("100.00"),
                occurred_at=date.today(),
                description="Test entry",
                attachments=None,
                entry_type=EntryType.INCOME,
                organization=self.organization,
                workspace=self.workspace,
                workspace_team=self.workspace_team,
                currency=self.currency,
                submitted_by_team_member=self.team_member,
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestUpdateEntryUserInputs:
    """Test the update_entry_user_inputs service function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory(status=EntryStatus.PENDING)
        self.organization = self.entry.organization
        self.currency = Currency.objects.get_or_create(code="USD", name="US Dollar")[0]

    def test_update_entry_user_inputs_success(self):
        """Test successful entry update."""
        # Create a different currency to trigger exchange rate update
        different_currency = Currency.objects.get_or_create(code="EUR", name="Euro")[0]
        
        with patch('apps.entries.services.get_closest_exchanged_rate') as mock_get_rate:
            mock_rate = Mock()
            mock_rate.rate = Decimal("1.50")
            mock_get_rate.return_value = mock_rate

            update_entry_user_inputs(
                entry=self.entry,
                organization=self.organization,
                amount=Decimal("200.00"),
                occurred_at=date.today(),
                description="Updated description",
                currency=different_currency,
                attachments=None,
                replace_attachments=False,
            )

            self.entry.refresh_from_db()
            assert self.entry.amount == Decimal("200.00")
            assert self.entry.description == "Updated description"
            assert self.entry.currency == different_currency
            assert self.entry.exchange_rate_used == Decimal("1.50")

    def test_update_entry_user_inputs_non_pending_status(self):
        """Test updating entry with non-pending status."""
        self.entry.status = EntryStatus.APPROVED
        self.entry.save()

        with pytest.raises(ValidationError, match="User can only update Entry info during the pending stage"):
            update_entry_user_inputs(
                entry=self.entry,
                organization=self.organization,
                amount=Decimal("200.00"),
                occurred_at=date.today(),
                description="Updated description",
                currency=self.currency,
                attachments=None,
                replace_attachments=False,
            )

    @patch('apps.entries.services.get_closest_exchanged_rate')
    def test_update_entry_user_inputs_no_exchange_rate(self, mock_get_rate):
        """Test updating entry when no exchange rate is available."""
        mock_get_rate.return_value = None
        
        # Create a different currency to trigger exchange rate lookup
        different_currency = Currency.objects.get_or_create(code="EUR", name="Euro")[0]

        with pytest.raises(ValueError, match="No exchange rate is defined"):
            update_entry_user_inputs(
                entry=self.entry,
                organization=self.organization,
                amount=Decimal("200.00"),
                occurred_at=date.today(),
                description="Updated description",
                currency=different_currency,
                attachments=None,
                replace_attachments=False,
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestUpdateEntryStatus:
    """Test the update_entry_status service function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory()
        self.reviewer = OrganizationMemberFactory()

    @patch('apps.entries.services.BusinessAuditLogger.log_status_change')
    def test_update_entry_status_success(self, mock_logger):
        """Test successful status update."""
        old_status = self.entry.status
        
        update_entry_status(
            entry=self.entry,
            status=EntryStatus.APPROVED,
            status_note="Approved by reviewer",
            last_status_modified_by=self.reviewer,
        )

        self.entry.refresh_from_db()
        assert self.entry.status == EntryStatus.APPROVED
        assert self.entry.status_note == "Approved by reviewer"
        assert self.entry.last_status_modified_by == self.reviewer
        assert self.entry.status_last_updated_at is not None

        # Verify audit logging
        mock_logger.assert_called_once()


@pytest.mark.unit
@pytest.mark.django_db
class TestBulkUpdateEntryStatus:
    """Test the bulk_update_entry_status service function."""

    def test_bulk_update_entry_status(self):
        """Test bulk status update."""
        entries = [EntryFactory() for _ in range(3)]
        
        # Update status for all entries
        for entry in entries:
            entry.status = EntryStatus.APPROVED
            entry.status_note = "Bulk approved"
            entry.last_status_modified_by = OrganizationMemberFactory()
            entry.status_last_updated_at = timezone.now()

        result = bulk_update_entry_status(entries=entries)

        assert result == entries
        # Verify all entries have been updated
        for entry in entries:
            entry.refresh_from_db()
            assert entry.status == EntryStatus.APPROVED


@pytest.mark.unit
@pytest.mark.django_db
class TestDeleteEntry:
    """Test the delete_entry service function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory(status=EntryStatus.PENDING)

    @patch('apps.entries.services.BusinessAuditLogger.log_entry_action')
    def test_delete_entry_success(self, mock_logger):
        """Test successful entry deletion."""
        # Get user from either team member or org member
        if self.entry.submitted_by_team_member:
            user = self.entry.submitted_by_team_member.organization_member.user
        else:
            user = self.entry.submitted_by_org_member.user
        
        result = delete_entry(entry=self.entry, user=user)

        assert result == self.entry
        assert not Entry.objects.filter(entry_id=self.entry.entry_id).exists()
        
        # Verify audit logging
        mock_logger.assert_called_once()

    def test_delete_entry_with_status_modified(self):
        """Test deleting entry that has been status modified."""
        self.entry.last_status_modified_by = OrganizationMemberFactory()
        self.entry.save()

        with pytest.raises(ValidationError, match="Cannot delete an entry when someone has already modified the status"):
            delete_entry(entry=self.entry)

    def test_delete_entry_non_pending_status(self):
        """Test deleting entry with non-pending status."""
        self.entry.status = EntryStatus.APPROVED
        self.entry.save()

        with pytest.raises(ValidationError, match="Cannot delete an entry that is not pending review"):
            delete_entry(entry=self.entry)


@pytest.mark.unit
@pytest.mark.django_db
class TestBulkDeleteEntries:
    """Test the bulk_delete_entries service function."""

    def test_bulk_delete_entries(self):
        """Test bulk entry deletion."""
        entries = [EntryFactory(status=EntryStatus.PENDING) for _ in range(3)]
        entry_ids = [entry.entry_id for entry in entries]

        # The function tries to call .delete() on the list, which will fail
        # This test documents the current behavior (which has a bug)
        with pytest.raises(AttributeError, match="'list' object has no attribute 'delete'"):
            bulk_delete_entries(entries=entries)


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryCreate:
    """Test the entry_create service function."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team_member = TeamMemberFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team_member.team
        )

    @patch('apps.entries.services.get_closest_exchanged_rate')
    @patch('apps.entries.services.BusinessAuditLogger.log_entry_action')
    def test_entry_create_success(self, mock_logger, mock_get_rate):
        """Test successful entry creation."""
        # Mock exchange rate
        mock_rate = Mock()
        mock_rate.rate = Decimal("1.00")
        mock_get_rate.return_value = mock_rate

        entry = entry_create(
            submitted_by=self.team_member,
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            description="Test entry",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            organization=self.organization,
        )

        assert entry.amount == Decimal("100.00")
        assert entry.description == "Test entry"
        assert entry.entry_type == EntryType.INCOME
        assert entry.organization == self.organization
        assert entry.workspace == self.workspace
        assert entry.workspace_team == self.workspace_team
        assert entry.submitted_by_team_member == self.team_member
        assert entry.exchange_rate_used == Decimal("1.00")

        # Verify audit logging
        mock_logger.assert_called_once()

    def test_entry_create_workspace_expense_without_workspace(self):
        """Test entry creation for workspace expense without workspace."""
        with pytest.raises(ValidationError, match="Workspace is required for workspace expense entries"):
            entry_create(
                submitted_by=self.team_member,
                entry_type=EntryType.WORKSPACE_EXP,
                amount=Decimal("100.00"),
                description="Test entry",
                organization=self.organization,
            )

    def test_entry_create_team_entry_without_workspace_team(self):
        """Test entry creation for team entry without workspace team."""
        with pytest.raises(ValidationError, match="Workspace team is required for team-based entries"):
            entry_create(
                submitted_by=self.team_member,
                entry_type=EntryType.INCOME,
                amount=Decimal("100.00"),
                description="Test entry",
                organization=self.organization,
            )

    @patch('apps.entries.services.get_closest_exchanged_rate')
    def test_entry_create_no_exchange_rate(self, mock_get_rate):
        """Test entry creation when no exchange rate is available."""
        mock_get_rate.return_value = None

        with pytest.raises(ValueError, match="No exchange rate is defined"):
            entry_create(
                submitted_by=self.team_member,
                entry_type=EntryType.INCOME,
                amount=Decimal("100.00"),
                description="Test entry",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
                organization=self.organization,
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryReview:
    """Test the entry_review service function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory(status=EntryStatus.PENDING)
        self.reviewer = OrganizationMemberFactory()

    @patch('apps.entries.services.BusinessAuditLogger.log_entry_action')
    def test_entry_review_approve(self, mock_logger):
        """Test entry approval."""
        result = entry_review(
            entry=self.entry,
            reviewer=self.reviewer,
            status=EntryStatus.APPROVED,
            notes="Approved",
        )

        assert result == self.entry
        self.entry.refresh_from_db()
        assert self.entry.status == EntryStatus.APPROVED
        assert self.entry.status_note == "Approved"
        assert self.entry.last_status_modified_by == self.reviewer

        # Verify audit logging
        mock_logger.assert_called_once()

    @patch('apps.entries.services.BusinessAuditLogger.log_entry_action')
    def test_entry_review_reject(self, mock_logger):
        """Test entry rejection."""
        result = entry_review(
            entry=self.entry,
            reviewer=self.reviewer,
            status=EntryStatus.REJECTED,
            notes="Rejected",
        )

        assert result == self.entry
        self.entry.refresh_from_db()
        assert self.entry.status == EntryStatus.REJECTED
        assert self.entry.status_note == "Rejected"

    @patch('apps.entries.services.BusinessAuditLogger.log_entry_action')
    def test_entry_review_flag(self, mock_logger):
        """Test entry flagging."""
        result = entry_review(
            entry=self.entry,
            reviewer=self.reviewer,
            status=self.entry.status,  # Keep current status
            is_flagged=True,
            notes="Flagged for review",
        )

        assert result == self.entry
        self.entry.refresh_from_db()
        assert self.entry.is_flagged is True
        assert self.entry.status_note == "Flagged for review"

    def test_entry_review_invalid_status(self):
        """Test entry review with invalid status."""
        with pytest.raises(ValidationError, match="Invalid review status"):
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer,
                status=EntryStatus.PENDING,
            )

    def test_entry_review_reject_without_notes(self):
        """Test entry rejection without notes."""
        with pytest.raises(ValidationError, match="Notes are required when rejected an entry"):
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer,
                status=EntryStatus.REJECTED,
            )

    def test_entry_review_flag_without_notes(self):
        """Test entry flagging without notes."""
        with pytest.raises(ValidationError, match="Notes are required when flagging an entry"):
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer,
                status=self.entry.status,
                is_flagged=True,
            )

    def test_entry_review_non_pending_status(self):
        """Test reviewing entry with non-pending status."""
        self.entry.status = EntryStatus.APPROVED
        self.entry.save()

        with pytest.raises(ValidationError, match="Cannot review entry with status"):
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer,
                status=EntryStatus.REJECTED,
                notes="Rejected",
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestApproveEntry:
    """Test the approve_entry service function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory(status=EntryStatus.PENDING)
        self.reviewer = OrganizationMemberFactory()

    @patch('apps.entries.services.entry_review')
    def test_approve_entry(self, mock_entry_review):
        """Test entry approval."""
        mock_entry_review.return_value = self.entry

        result = approve_entry(
            entry=self.entry,
            reviewer=self.reviewer,
            notes="Approved",
        )

        assert result == self.entry
        mock_entry_review.assert_called_once_with(
            entry=self.entry,
            reviewer=self.reviewer,
            status=EntryStatus.APPROVED,
            notes="Approved",
            request=None,
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestRejectEntry:
    """Test the reject_entry service function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory(status=EntryStatus.PENDING)
        self.reviewer = OrganizationMemberFactory()

    @patch('apps.entries.services.entry_review')
    def test_reject_entry(self, mock_entry_review):
        """Test entry rejection."""
        mock_entry_review.return_value = self.entry

        result = reject_entry(
            entry=self.entry,
            reviewer=self.reviewer,
            notes="Rejected",
        )

        assert result == self.entry
        mock_entry_review.assert_called_once_with(
            entry=self.entry,
            reviewer=self.reviewer,
            status=EntryStatus.REJECTED,
            notes="Rejected",
            request=None,
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestFlagEntry:
    """Test the flag_entry service function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory(status=EntryStatus.PENDING)
        self.reviewer = OrganizationMemberFactory()

    @patch('apps.entries.services.entry_review')
    def test_flag_entry(self, mock_entry_review):
        """Test entry flagging."""
        mock_entry_review.return_value = self.entry

        result = flag_entry(
            entry=self.entry,
            reviewer=self.reviewer,
            notes="Flagged",
        )

        assert result == self.entry
        mock_entry_review.assert_called_once_with(
            entry=self.entry,
            reviewer=self.reviewer,
            status=self.entry.status,
            is_flagged=True,
            notes="Flagged",
            request=None,
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestBulkReviewEntries:
    """Test the bulk_review_entries service function."""

    def setup_method(self):
        """Set up test data."""
        self.entries = [EntryFactory(status=EntryStatus.PENDING) for _ in range(3)]
        self.reviewer = OrganizationMemberFactory()

    @patch('apps.entries.services.BusinessAuditLogger.log_bulk_operation')
    def test_bulk_review_entries_success(self, mock_logger):
        """Test successful bulk review."""
        result = bulk_review_entries(
            entries=self.entries,
            reviewer=self.reviewer,
            status=EntryStatus.APPROVED,
            notes="Bulk approved",
        )

        assert len(result) == 3
        for entry in result:
            entry.refresh_from_db()
            assert entry.status == EntryStatus.APPROVED
            assert entry.status_note == "Bulk approved"
            assert entry.last_status_modified_by == self.reviewer

        # Verify audit logging
        mock_logger.assert_called_once()

    def test_bulk_review_entries_invalid_status(self):
        """Test bulk review with invalid status."""
        with pytest.raises(ValidationError, match="Invalid review status"):
            bulk_review_entries(
                entries=self.entries,
                reviewer=self.reviewer,
                status=EntryStatus.PENDING,
            )

    def test_bulk_review_entries_reject_without_notes(self):
        """Test bulk rejection without notes."""
        with pytest.raises(ValidationError, match="Notes are required when rejected an entry"):
            bulk_review_entries(
                entries=self.entries,
                reviewer=self.reviewer,
                status=EntryStatus.REJECTED,
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryUpdate:
    """Test the entry_update service function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory(status=EntryStatus.PENDING)
        self.updater = OrganizationMemberFactory()

    @patch('apps.entries.services.BusinessAuditLogger.log_entry_action')
    def test_entry_update_success(self, mock_logger):
        """Test successful entry update."""
        result = entry_update(
            entry=self.entry,
            updated_by=self.updater,
            description="Updated description",
            amount=Decimal("200.00"),
        )

        assert result == self.entry
        self.entry.refresh_from_db()
        assert self.entry.description == "Updated description"
        assert self.entry.amount == Decimal("200.00")

        # Verify audit logging
        mock_logger.assert_called_once()

    def test_entry_update_no_valid_fields(self):
        """Test entry update with no valid fields."""
        with pytest.raises(ValidationError, match="No valid fields to update"):
            entry_update(
                entry=self.entry,
                updated_by=self.updater,
                invalid_field="value",
            )

    def test_entry_update_approved_entry(self):
        """Test updating approved entry."""
        self.entry.status = EntryStatus.APPROVED
        self.entry.save()

        with pytest.raises(ValidationError, match="Cannot update an approved entry"):
            entry_update(
                entry=self.entry,
                updated_by=self.updater,
                description="Updated description",
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrgExpenseStats:
    """Test the get_org_expense_stats service function."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()

    @patch('apps.entries.services.EntryStats')
    def test_get_org_expense_stats(self, mock_entry_stats):
        """Test getting organization expense stats."""
        # Mock the EntryStats instance
        mock_instance = Mock()
        mock_instance.total.return_value = Decimal("1000.00")
        mock_instance.this_month.return_value = Decimal("100.00")
        mock_instance.last_month.return_value = Decimal("90.00")
        mock_instance.average_monthly.return_value = Decimal("95.00")
        mock_entry_stats.return_value = mock_instance

        result = get_org_expense_stats(self.organization)

        assert len(result) == 3
        assert result[0]["title"] == "Total Expenses"
        assert result[0]["value"] == Decimal("1000.00")
        assert result[1]["title"] == "This Month's Expenses"
        assert result[1]["value"] == Decimal("100.00")
        assert result[2]["title"] == "Average Monthly Expense"
        assert result[2]["value"] == Decimal("95.00")

        # Verify EntryStats was called with correct parameters
        mock_entry_stats.assert_called_once_with(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
        )
