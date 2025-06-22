"""
Unit tests for Entry service business logic.

Tests entry_create service function validation and business rules.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError

from apps.entries.models import EntryStatus, EntryType
from apps.entries.services import (
    approve_entry,
    bulk_review_entries,
    create_org_expense_entry_with_attachments,
    entry_create,
    entry_review,
    entry_update,
    flag_entry,
    reject_entry,
)
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    OrganizationMemberFactory,
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
        self.workspace = WorkspaceFactory(
            organization=self.submitter.organization_member.organization
        )
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.submitter.team
        )

    def test_entry_create_with_valid_submitter(self):
        """Test entry creation with valid submitter role."""
        entry = entry_create(
            submitted_by=self.submitter,
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            description="Test donation",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert entry.submitter == self.submitter
        assert entry.entry_type == EntryType.INCOME
        assert entry.amount == Decimal("100.00")
        assert entry.description == "Test donation"
        assert entry.status == "pending_review"  # Default status

    def test_entry_create_fails_with_zero_amount(self):
        """Test entry creation fails with zero amount."""
        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=self.submitter,
                entry_type=EntryType.INCOME,
                amount=Decimal("0.00"),
                description="Test donation",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
            )

        assert "Ensure this value is greater than or equal to 0.01" in str(exc_info.value)  

    def test_entry_create_fails_with_negative_amount(self):
        """Test entry creation fails with negative amount."""
        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=self.submitter,
                entry_type=EntryType.INCOME,
                amount=Decimal("-50.00"),
                description="Test donation",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
            )

        assert "Ensure this value is greater than or equal to 0.01" in str(exc_info.value)

    def test_entry_create_with_different_entry_types(self):
        """Test entry creation with different entry types."""
        entry_types = [EntryType.INCOME, EntryType.DISBURSEMENT, EntryType.REMITTANCE]

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
            entry_type=EntryType.INCOME,
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
            entry_type=EntryType.DISBURSEMENT,
            amount=Decimal("0.01"),
            description="Small expense",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        assert entry.amount == Decimal("0.01")

    def test_entry_create_with_long_description(self):
        """Test entry creation with maximum length description."""
        # Max length is 255 characters
        long_description = "x" * 255

        entry = entry_create(
            submitted_by=self.submitter,
            entry_type=EntryType.INCOME,
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
            entry_type=EntryType.INCOME,
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
                "entry_type": EntryType.INCOME,
                "amount": "150.00",
                "description": "Test entry",
            },
        )

    def test_entry_create_fails_without_workspace_for_workspace_expense(self):
        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=self.submitter,
                entry_type=EntryType.WORKSPACE_EXP,
                amount=Decimal("100.00"),
                description="Test workspace expense",
                workspace_team=self.workspace_team,
            )

        assert "Workspace is required for workspace expense entries" in str(exc_info.value)

    def test_entry_create_fails_without_workspace_team_for_team_entries(self):
        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=self.submitter,
                entry_type=EntryType.INCOME,
                amount=Decimal("100.00"),
                description="Test donation",
                workspace=self.workspace,
            )

        assert "Workspace team is required for team-based entries" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryReviewService:
    """Test entry_review service business logic."""

    def setup_method(self, method):
        """Set up test data."""
        self.submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        self.reviewer = TeamMemberFactory(
            role=TeamMemberRole.OPERATIONS_REVIEWER, team=self.submitter.team
        )
        self.workspace = WorkspaceFactory(
            organization=self.submitter.organization_member.organization
        )
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.submitter.team
        )

        self.entry = entry_create(
            submitted_by=self.submitter,
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            description="Test donation",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

    def test_entry_review_approve(self):
        """Test entry review approval."""
        reviewed_entry = entry_review(
            entry=self.entry,
            reviewer=self.reviewer.organization_member,
            status=EntryStatus.APPROVED,
        )

        assert reviewed_entry.status == EntryStatus.APPROVED
        assert reviewed_entry.reviewed_by == self.reviewer.organization_member
        assert reviewed_entry.review_notes == ""

    def test_entry_review_reject_with_notes(self):
        """Test entry review rejection with notes."""
        notes = "Missing receipt"
        reviewed_entry = entry_review(
            entry=self.entry,
            reviewer=self.reviewer.organization_member,
            status=EntryStatus.REJECTED,
            notes=notes,
        )

        assert reviewed_entry.status == EntryStatus.REJECTED
        assert reviewed_entry.reviewed_by == self.reviewer.organization_member
        assert reviewed_entry.review_notes == notes

    def test_entry_review_flag_with_notes(self):
        """Test entry review flag with notes."""
        notes = "Missing receipt"
        reviewed_entry = entry_review(
            entry=self.entry,
            reviewer=self.reviewer.organization_member,
            status=EntryStatus.FLAGGED,
            notes=notes,
        )

        assert reviewed_entry.status == EntryStatus.FLAGGED
        assert reviewed_entry.reviewed_by == self.reviewer.organization_member
        assert reviewed_entry.review_notes == notes

    def test_entry_review_invalid_status(self):
        """Test entry review fails with invalid status."""
        with pytest.raises(ValidationError) as exc_info:
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer.organization_member,
                status="invalid_status",
            )

        assert "Invalid review status" in str(exc_info.value)

    def test_entry_review_reject_without_notes(self):
        """Test entry review reject without notes."""
        with pytest.raises(ValidationError) as exc_info:
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer.organization_member,
                status=EntryStatus.REJECTED,
            )

        assert "Notes are required when rejected an entry" in str(exc_info.value)

    def test_entry_review_flag_without_notes(self):
        """Test entry review flag without notes."""
        with pytest.raises(ValidationError) as exc_info:
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer.organization_member,
                status=EntryStatus.FLAGGED,
            )

        assert "Notes are required when flagged an entry" in str(exc_info.value)

    def test_entry_review_already_approved_entry(self):
        """Test entry review fails with already approved entry."""
        approved_entry = entry_review(
            entry=self.entry,
            reviewer=self.reviewer.organization_member,
            status=EntryStatus.APPROVED,
        )

        with pytest.raises(ValidationError) as exc_info:
            entry_review(
                entry=approved_entry,
                reviewer=self.reviewer.organization_member,
                status=EntryStatus.REJECTED,
                notes="Changed my mind",
            )

        assert "Cannot review entry with status: approved" in str(exc_info.value)

    @patch("apps.entries.services.entry_review")
    def test_approve_entry(self, mock_entry_review):
        """Test approve_entry calls entry_review with correct params."""

        entry = self.entry
        reviewer = self.reviewer.organization_member

        approve_entry(entry=entry, reviewer=reviewer)

        mock_entry_review.assert_called_once_with(
            entry=entry, reviewer=reviewer, status=EntryStatus.APPROVED, notes=None
        )

    @patch("apps.entries.services.entry_review")
    def test_reject_entry(self, mock_entry_review):
        """Test reject_entry calls entry_review with correct params."""

        entry = self.entry
        reviewer = self.reviewer.organization_member
        notes = "Missing documentation"

        reject_entry(entry=entry, reviewer=reviewer, notes=notes)

        mock_entry_review.assert_called_once_with(
            entry=entry, reviewer=reviewer, status=EntryStatus.REJECTED, notes=notes
        )

    @patch("apps.entries.services.entry_review")
    def test_flag_entry(self, mock_entry_review):
        """Test flag_entry calls entry_review with correct params."""

        entry = self.entry
        reviewer = self.reviewer.organization_member
        notes = "Needs further review"

        flag_entry(entry=entry, reviewer=reviewer, notes=notes)

        mock_entry_review.assert_called_once_with(
            entry=entry, reviewer=reviewer, status=EntryStatus.FLAGGED, notes=notes
        )

    def test_bulk_review_entries(self):
        """Test bulk review entries."""

        entries = []
        for i in range(3):
            entry = entry_create(
                submitted_by=self.submitter,
                entry_type=EntryType.INCOME,
                amount=Decimal("100.00"),
                description=f"Test donation {i}",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
            )
            entries.append(entry)

        approved_entry = entry_create(
            submitted_by=self.submitter,
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            description="Test donation",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )
        approved_entry.status = EntryStatus.APPROVED
        approved_entry.save()
        entries.append(approved_entry)

        notes = "Bulk approval"
        reviewed_entries = bulk_review_entries(
            entries=entries,
            reviewer=self.reviewer.organization_member,
            status=EntryStatus.APPROVED,
            notes=notes,
        )

        assert len(reviewed_entries) == 3
        for entry in reviewed_entries:
            assert entry.status == EntryStatus.APPROVED
            assert entry.reviewed_by == self.reviewer.organization_member
            assert entry.review_notes == notes

    def test_bulk_review_entries_with_rejection(self):
        """Test bulk rejecting entries."""
        entries = []
        for i in range(3):
            entry = entry_create(
                submitted_by=self.submitter,
                entry_type=EntryType.INCOME,
                amount=Decimal("100.00"),
                description=f"Test donation {i}",
                workspace=self.workspace,
                workspace_team=self.workspace_team,
            )
            entries.append(entry)

        notes = "Bulk rejection - missing documentation"
        reviewed_entries = bulk_review_entries(
            entries=entries,
            reviewer=self.reviewer.organization_member,
            status=EntryStatus.REJECTED,
            notes=notes,
        )

        assert len(reviewed_entries) == 3
        for entry in reviewed_entries:
            assert entry.status == EntryStatus.REJECTED
            assert entry.reviewed_by == self.reviewer.organization_member
            assert entry.review_notes == notes

    def test_bulk_review_entries_reject_without_notes(self):
        """Test bulk rejection requires notes."""
        entries = [self.entry]

        with pytest.raises(ValidationError) as exc_info:
            bulk_review_entries(
                entries=entries,
                reviewer=self.reviewer.organization_member,
                status=EntryStatus.REJECTED,
            )

        assert "Notes are required when rejected an entry" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryUpdateService:
    """Test entry_update service business logic."""

    def setup_method(self, method):
        """Set up test data."""
        self.submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        self.workspace = WorkspaceFactory(
            organization=self.submitter.organization_member.organization
        )
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.submitter.team
        )

        self.entry = entry_create(
            submitted_by=self.submitter,
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            description="Original description",
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

    def test_entry_update_valid_fields(self):
        """Test entry update with valid fields."""
        new_description = "Updated description"
        new_amount = Decimal("150.00")

        updated_entry = entry_update(
            entry=self.entry,
            updated_by=self.submitter.organization_member.user,
            description=new_description,
            amount=new_amount,
        )

        assert updated_entry.description == new_description
        assert updated_entry.amount == new_amount

    def test_entry_update_no_valid_fields(self):
        """Test entry update with no valid fields."""
        with pytest.raises(ValidationError) as exc_info:
            entry_update(
                entry=self.entry,
                updated_by=self.submitter.organization_member.user,
                invalid_field="This is an invalid field",
            )

        assert "No valid fields to update" in str(exc_info.value)

    def test_entry_update_approved_entry(self):
        """Test entry update with approved entry."""
        self.entry.status = EntryStatus.APPROVED
        self.entry.save()

        with pytest.raises(ValidationError) as exc_info:
            entry_update(
                entry=self.entry,
                updated_by=self.submitter.organization_member.user,
                description="Updated description",
            )

        assert "Cannot update an approved entry" in str(exc_info.value)

    @patch("apps.entries.services.audit_create")
    def test_entry_update_calls_audit_service(self, mock_audit_create):
        """Test that entry_update calls audit service with correct params."""
        updated_entry = entry_update(
            entry=self.entry,
            updated_by=self.submitter.organization_member.user,
            description="Updated description",
        )

        mock_audit_create.assert_called_once_with(
            user=self.submitter.organization_member.user,
            action_type="entry_updated",
            target_entity=updated_entry,
            metadata={
                "updated_fields": ["description"],
            },
        )

    def test_entry_update_workspace_and_team(self):
        """Test updating workspace and workspace_team."""
        new_workspace = WorkspaceFactory(
            organization=self.submitter.organization_member.organization
        )
        new_workspace_team = WorkspaceTeamFactory(
            workspace=new_workspace, team=self.submitter.team
        )

        updated_entry = entry_update(
            entry=self.entry,
            updated_by=self.submitter.organization_member.user,
            workspace=new_workspace,
            workspace_team=new_workspace_team,
        )

        assert updated_entry.workspace == new_workspace
        assert updated_entry.workspace_team == new_workspace_team


@pytest.mark.unit
@pytest.mark.django_db
class TestCreateOrgExpenseEntryService:
    """Test create_org_expense_entry_with_attachments service."""
    
    def setup_method(self, method):
        """Set up test data."""
        self.org_member = OrganizationMemberFactory()
    
    @patch("apps.entries.services.Attachment.objects.create")
    @patch("apps.attachments.constants.AttachmentType.get_file_type_by_extension")
    def test_create_org_expense_entry_with_attachments(self, mock_get_file_type, mock_attachment_create):
        """Test creating an org expense entry with attachments."""
        from apps.attachments.constants import AttachmentType
        
        # Create mock files
        mock_file1 = MagicMock()
        mock_file1.name = "receipt.pdf"
        mock_file2 = MagicMock()
        mock_file2.name = "invoice.jpg"
        
        # Setup mock return values
        mock_get_file_type.side_effect = [AttachmentType.PDF, AttachmentType.IMAGE]
        mock_attachment_create.return_value = MagicMock()
        
        # Call the service function
        entry = create_org_expense_entry_with_attachments(
            org_member=self.org_member,
            amount=Decimal("200.00"),
            description="Office supplies",
            attachments=[mock_file1, mock_file2],
        )
        
        # Verify entry was created correctly
        assert entry.entry_type == EntryType.ORG_EXP
        assert entry.amount == Decimal("200.00")
        assert entry.status == EntryStatus.APPROVED
        
        # Verify attachment creation was called
        assert mock_attachment_create.call_count == 2
        mock_attachment_create.assert_any_call(
            entry=entry, 
            file_url=mock_file1, 
            file_type=AttachmentType.PDF
        )
        mock_attachment_create.assert_any_call(
            entry=entry, 
            file_url=mock_file2, 
            file_type=AttachmentType.IMAGE
        )