"""
Unit tests for Entry service business logic.

Tests entry_create service function validation and business rules.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from guardian.shortcuts import assign_perm, remove_perm

from apps.entries.models import EntryStatus, EntryType
from apps.entries.permissions import EntryPermissions
from apps.entries.services import (
    approve_entry,
    bulk_review_entries,
    entry_create,
    entry_review,
    entry_update,
    flag_entry,
    reject_entry,
)
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    EntryFactory,
    TeamMemberFactory,
)
from tests.factories.team_factories import TeamFactory
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceTeamFactory,
)
from tests.factories.organization_factories import OrganizationMemberFactory


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
        assign_perm(
            EntryPermissions.ADD_ENTRY,
            self.submitter.organization_member.user,
            self.workspace,
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
        assert entry.status == EntryStatus.PENDING_REVIEW  # Default status

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

        assert "Ensure this value is greater than or equal to 0.01" in str(
            exc_info.value
        )

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

        assert "Ensure this value is greater than or equal to 0.01" in str(
            exc_info.value
        )

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
            )

        assert "Workspace is required for workspace expense entries" in str(
            exc_info.value
        )

    def test_entry_create_fails_without_workspace_team_for_team_entries(self):
        with pytest.raises(ValidationError) as exc_info:
            entry_create(
                submitted_by=self.submitter,
                entry_type=EntryType.INCOME,
                amount=Decimal("100.00"),
                description="Test donation",
                workspace=self.workspace,
            )

        assert "Workspace team is required for team-based entries" in str(
            exc_info.value
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryReviewService:
    """Test entry_review service business logic."""

    def setup_method(self, method):
        """Set up test data."""
        self.submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        self.reviewer = OrganizationMemberFactory()
        self.workspace = WorkspaceFactory(
            organization=self.submitter.organization_member.organization,
            operation_reviewer=self.reviewer,
        )
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.submitter.team
        )
        assign_perm(
            EntryPermissions.ADD_ENTRY,
            self.submitter.organization_member.user,
            self.workspace,
        )
        assign_perm(EntryPermissions.REVIEW_ENTRY, self.reviewer.user, self.workspace)

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
            reviewer=self.reviewer,
            status=EntryStatus.APPROVED,
        )

        assert reviewed_entry.status == EntryStatus.APPROVED
        assert reviewed_entry.reviewed_by == self.reviewer
        assert reviewed_entry.review_notes == ""

    def test_entry_review_reject_with_notes(self):
        """Test entry review rejection with notes."""
        notes = "Missing receipt"
        reviewed_entry = entry_review(
            entry=self.entry,
            reviewer=self.reviewer,
            status=EntryStatus.REJECTED,
            notes=notes,
        )

        assert reviewed_entry.status == EntryStatus.REJECTED
        assert reviewed_entry.reviewed_by == self.reviewer
        assert reviewed_entry.review_notes == notes

    def test_entry_review_flag_with_notes(self):
        """Test entry review flag with notes."""
        notes = "Missing receipt"
        reviewed_entry = entry_review(
            entry=self.entry,
            reviewer=self.reviewer,
            status=self.entry.status,
            is_flagged=True,
            notes=notes,
        )

        assert reviewed_entry.is_flagged
        assert reviewed_entry.reviewed_by == self.reviewer
        assert reviewed_entry.review_notes == notes

    def test_entry_review_invalid_status(self):
        """Test entry review fails with invalid status."""
        with pytest.raises(ValidationError) as exc_info:
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer,
                status="invalid_status",
            )

        assert "Invalid review status" in str(exc_info.value)

    def test_entry_review_reject_without_notes(self):
        """Test entry review reject without notes."""
        with pytest.raises(ValidationError) as exc_info:
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer,
                status=EntryStatus.REJECTED,
            )

        assert "Notes are required when rejected an entry" in str(exc_info.value)

    def test_entry_review_flag_without_notes(self):
        """Test entry review flag without notes."""
        with pytest.raises(ValidationError) as exc_info:
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer,
                status=self.entry.status,
                is_flagged=True,
            )

        assert "Notes are required when flagging an entry" in str(exc_info.value)

    def test_entry_review_already_approved_entry(self):
        """Test entry review fails with already approved entry."""
        self.entry.status = EntryStatus.APPROVED
        self.entry.save()

        with pytest.raises(ValidationError) as exc_info:
            entry_review(
                entry=self.entry,
                reviewer=self.reviewer,
                status=EntryStatus.REJECTED,
                notes="Changed my mind",
            )

        assert "Cannot review entry with status: approved" in str(exc_info.value)

    @patch("apps.entries.services.entry_review")
    def test_approve_entry(self, mock_entry_review):
        """Test approve_entry calls entry_review with correct params."""

        entry = self.entry
        reviewer = self.reviewer

        approve_entry(entry=entry, reviewer=reviewer)

        mock_entry_review.assert_called_once_with(
            entry=entry, reviewer=reviewer, status=EntryStatus.APPROVED, notes=None
        )

    @patch("apps.entries.services.entry_review")
    def test_reject_entry(self, mock_entry_review):
        """Test reject_entry calls entry_review with correct params."""

        entry = self.entry
        reviewer = self.reviewer
        notes = "Missing documentation"

        reject_entry(entry=entry, reviewer=reviewer, notes=notes)

        mock_entry_review.assert_called_once_with(
            entry=entry, reviewer=reviewer, status=EntryStatus.REJECTED, notes=notes
        )

    @patch("apps.entries.services.entry_review")
    def test_flag_entry(self, mock_entry_review):
        """Test flag_entry calls entry_review with correct params."""

        entry = self.entry
        reviewer = self.reviewer
        notes = "Needs further review"

        flag_entry(entry=entry, reviewer=reviewer, notes=notes)

        mock_entry_review.assert_called_once_with(
            entry=entry, reviewer=reviewer, status=entry.status, is_flagged=True, notes=notes
        )

    def test_bulk_review_entries(self):
        """Test bulk review entries."""

        entries = [EntryFactory(workspace=self.workspace) for _ in range(3)]

        approved_entry = EntryFactory(
            workspace=self.workspace, status=EntryStatus.APPROVED
        )
        entries.append(approved_entry)

        notes = "Bulk approval"
        reviewed_entries = bulk_review_entries(
            entries=entries,
            reviewer=self.reviewer,
            status=EntryStatus.APPROVED,
            notes=notes,
        )

        assert len(reviewed_entries) == 3
        for entry in reviewed_entries:
            entry.refresh_from_db()
            assert entry.status == EntryStatus.APPROVED
            assert entry.reviewed_by == self.reviewer
            assert entry.review_notes == notes

    def test_bulk_review_entries_with_rejection(self):
        """Test bulk rejecting entries."""
        entries = [EntryFactory(workspace=self.workspace) for _ in range(3)]

        notes = "Bulk rejection - missing documentation"
        reviewed_entries = bulk_review_entries(
            entries=entries,
            reviewer=self.reviewer,
            status=EntryStatus.REJECTED,
            notes=notes,
        )

        assert len(reviewed_entries) == 3
        for entry in reviewed_entries:
            entry.refresh_from_db()
            assert entry.status == EntryStatus.REJECTED
            assert entry.reviewed_by == self.reviewer
            assert entry.review_notes == notes

    def test_bulk_review_entries_reject_without_notes(self):
        """Test bulk rejection requires notes."""
        entries = [self.entry]

        with pytest.raises(ValidationError) as exc_info:
            bulk_review_entries(
                entries=entries,
                reviewer=self.reviewer,
                status=EntryStatus.REJECTED,
            )

        assert "Notes are required when rejected an entry" in str(exc_info.value)

    def test_coordinator_cannot_review_other_team_entry(self):
        """A coordinator for one team cannot review an entry from another team."""
        # Coordinator for a different team
        other_team = TeamFactory(organization=self.workspace.organization)
        coordinator = OrganizationMemberFactory(
            organization=self.workspace.organization
        )
        other_team.team_coordinator = coordinator
        other_team.save()

        assign_perm(EntryPermissions.REVIEW_ENTRY, coordinator.user, self.workspace)

        with pytest.raises(PermissionDenied) as exc_info:
            entry_review(
                entry=self.entry, reviewer=coordinator, status=EntryStatus.APPROVED
            )
        assert "You can only manage entries for your own team." in str(exc_info.value)

    def test_coordinator_can_review_own_team_entry(self):
        """A coordinator can review an entry from their own team."""
        # Coordinator for the entry's team
        coordinator = OrganizationMemberFactory(
            organization=self.workspace.organization
        )
        self.submitter.team.team_coordinator = coordinator
        self.submitter.team.save()

        assign_perm(EntryPermissions.REVIEW_ENTRY, coordinator.user, self.workspace)

        reviewed_entry = entry_review(
            entry=self.entry, reviewer=coordinator, status=EntryStatus.APPROVED
        )
        assert reviewed_entry.status == EntryStatus.APPROVED
        assert reviewed_entry.reviewed_by == coordinator

    def test_non_coordinator_reviewer_can_review_any_entry(self):
        """A user with review perms who is not a coordinator can review any entry."""
        # self.reviewer is an OrganizationMember without any team coordination roles
        reviewed_entry = entry_review(
            entry=self.entry, reviewer=self.reviewer, status=EntryStatus.APPROVED
        )
        assert reviewed_entry.status == EntryStatus.APPROVED
        assert reviewed_entry.reviewed_by == self.reviewer


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
        assign_perm(
            EntryPermissions.ADD_ENTRY,
            self.submitter.organization_member.user,
            self.workspace,
        )
        assign_perm(
            EntryPermissions.CHANGE_ENTRY,
            self.submitter.organization_member.user,
            self.workspace,
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
            updated_by=self.submitter,
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
                updated_by=self.submitter,
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
                updated_by=self.submitter,
                description="Updated description",
            )

        assert "Cannot update an approved entry" in str(exc_info.value)

    def test_entry_update_permission_denied(self):
        """Test entry update fails without correct permission."""
        remove_perm(
            EntryPermissions.CHANGE_ENTRY,
            self.submitter.organization_member.user,
            self.workspace,
        )

        with pytest.raises(PermissionDenied):
            entry_update(
                entry=self.entry,
                updated_by=self.submitter,
                description="This should fail",
            )

    @patch("apps.entries.services.audit_create")
    def test_entry_update_calls_audit_service(self, mock_audit_create):
        """Test that entry_update calls audit service with correct params."""
        updated_entry = entry_update(
            entry=self.entry,
            updated_by=self.submitter,
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

        assign_perm(
            EntryPermissions.CHANGE_ENTRY,
            self.submitter.organization_member.user,
            new_workspace,
        )

        updated_entry = entry_update(
            entry=self.entry,
            updated_by=self.submitter,
            workspace=new_workspace,
            workspace_team=new_workspace_team,
        )

        assert updated_entry.workspace == new_workspace
        assert updated_entry.workspace_team == new_workspace_team
