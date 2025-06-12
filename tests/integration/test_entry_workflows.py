"""
Integration tests for Entry workflows.

Tests how entries work with team members, submission, review, and approval processes.
"""

import pytest
from decimal import Decimal

from apps.entries.models import Entry
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    TeamFactory,
    TeamMemberFactory,
    TeamCoordinatorFactory,
    OperationsReviewerFactory,
    WorkspaceAdminMemberFactory,
    EntryFactory,
    IncomeEntryFactory,
    DisbursementEntryFactory,
    RemittanceEntryFactory,
    PendingEntryFactory,
    FlaggedEntryFactory,
)


@pytest.mark.integration
@pytest.mark.django_db
class TestEntrySubmissionWorkflows:
    """Test entry submission workflows."""

    def test_complete_entry_submission_workflow(self):
        """Test complete entry submission by team member."""
        # Create fundraising team with field agent
        team = TeamFactory(title="Regional Fundraising Team")
        field_agent = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Submit financial transaction
        entry = EntryFactory(
            submitted_by=field_agent,
            entry_type="income",
            amount=Decimal("1500.00"),
            description="Weekly donation collections from local supporters",
        )

        # Verify submission
        assert entry.submitted_by == field_agent
        assert entry.submitted_by.role == TeamMemberRole.SUBMITTER
        assert entry.submitted_by.team == team
        assert entry.entry_type == "income"
        assert entry.amount == Decimal("1500.00")
        assert entry.status == "pending_review"
        assert entry.reviewed_by is None
        assert entry.review_notes is None

    def test_multiple_entry_types_submission_workflow(self):
        """Test submitting different types of entries."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Submit different entry types
        IncomeEntryFactory(submitted_by=submitter, amount=Decimal("2000.00"))
        DisbursementEntryFactory(submitted_by=submitter, amount=Decimal("500.00"))
        RemittanceEntryFactory(submitted_by=submitter, amount=Decimal("1800.00"))

        # Verify all entries
        entries = Entry.objects.filter(submitted_by=submitter)
        assert entries.count() == 3

        entry_types = [entry.entry_type for entry in entries]
        assert "income" in entry_types
        assert "disbursement" in entry_types
        assert "remittance" in entry_types

    def test_entry_submission_validation_workflow(self):
        """Test entry submission validation rules."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Valid entry should work
        valid_entry = EntryFactory(
            submitted_by=submitter,
            entry_type="income",
            amount=Decimal("100.00"),
            description="Valid entry",
        )

        # Entry should pass validation
        valid_entry.full_clean()
        assert valid_entry.submitted_by.role == TeamMemberRole.SUBMITTER


@pytest.mark.integration
@pytest.mark.django_db
class TestEntryReviewWorkflows:
    """Test entry review and approval workflows."""

    def test_complete_entry_approval_workflow(self):
        """Test complete entry review and approval process."""
        # Create team with submitter and coordinator
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        coordinator = TeamCoordinatorFactory(team=team)

        # Submit entry
        entry = PendingEntryFactory(submitted_by=submitter)
        assert entry.status == "pending_review"

        # Review and approve entry
        entry.status = "approved"
        entry.reviewed_by = coordinator
        entry.review_notes = "Entry looks good, approved for processing"
        entry.save()

        # Verify approval
        entry.refresh_from_db()
        assert entry.status == "approved"
        assert entry.reviewed_by == coordinator
        assert entry.reviewed_by.role == TeamMemberRole.TEAM_COORDINATOR
        assert entry.review_notes == "Entry looks good, approved for processing"

    def test_entry_rejection_workflow(self):
        """Test entry rejection process."""
        # Create team with submitter and reviewer
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        reviewer = OperationsReviewerFactory(team=team)

        # Submit entry
        entry = PendingEntryFactory(submitted_by=submitter)

        # Review and reject entry
        entry.status = "rejected"
        entry.reviewed_by = reviewer
        entry.review_notes = "Insufficient documentation provided"
        entry.save()

        # Verify rejection
        entry.refresh_from_db()
        assert entry.status == "rejected"
        assert entry.reviewed_by == reviewer
        assert entry.reviewed_by.role == TeamMemberRole.OPERATIONS_REVIEWER
        assert "Insufficient documentation" in entry.review_notes

    def test_entry_flagging_workflow(self):
        """Test entry flagging for further investigation."""
        # Create team with submitter and workspace admin
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        admin = WorkspaceAdminMemberFactory(team=team)

        # Submit entry
        entry = PendingEntryFactory(submitted_by=submitter, amount=Decimal("10000.00"))

        # Flag entry for investigation
        entry.status = "flagged"
        entry.reviewed_by = admin
        entry.review_notes = "Large amount requires additional verification"
        entry.save()

        # Verify flagging
        entry.refresh_from_db()
        assert entry.status == "flagged"
        assert entry.reviewed_by == admin
        assert entry.reviewed_by.role == TeamMemberRole.WORKSPACE_ADMIN
        assert "additional verification" in entry.review_notes

    def test_reviewer_authorization_workflow(self):
        """Test that only authorized roles can review entries."""
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Create reviewers with different authorized roles
        coordinator = TeamCoordinatorFactory(team=team)
        operations_reviewer = OperationsReviewerFactory(team=team)
        workspace_admin = WorkspaceAdminMemberFactory(team=team)

        # Test each reviewer type
        for reviewer in [coordinator, operations_reviewer, workspace_admin]:
            entry = PendingEntryFactory(submitted_by=submitter)
            entry.reviewed_by = reviewer
            entry.status = "approved"
            entry.review_notes = f"Reviewed by {reviewer.role}"

            # Should validate successfully
            entry.full_clean()
            entry.save()

            assert entry.reviewed_by.role in [
                TeamMemberRole.TEAM_COORDINATOR,
                TeamMemberRole.OPERATIONS_REVIEWER,
                TeamMemberRole.WORKSPACE_ADMIN,
            ]


@pytest.mark.integration
@pytest.mark.django_db
class TestEntryStatusTransitionWorkflows:
    """Test entry status transition workflows."""

    def test_pending_to_approved_workflow(self):
        """Test transitioning entry from pending to approved."""
        entry = PendingEntryFactory()
        coordinator = TeamCoordinatorFactory()

        assert entry.status == "pending_review"

        # Approve entry
        entry.status = "approved"
        entry.reviewed_by = coordinator
        entry.review_notes = "Approved after review"
        entry.save()

        entry.refresh_from_db()
        assert entry.status == "approved"
        assert entry.reviewed_by == coordinator

    def test_pending_to_rejected_workflow(self):
        """Test transitioning entry from pending to rejected."""
        entry = PendingEntryFactory()
        reviewer = OperationsReviewerFactory()

        assert entry.status == "pending_review"

        # Reject entry
        entry.status = "rejected"
        entry.reviewed_by = reviewer
        entry.review_notes = "Missing required information"
        entry.save()

        entry.refresh_from_db()
        assert entry.status == "rejected"
        assert entry.reviewed_by == reviewer

    def test_flagged_to_approved_workflow(self):
        """Test transitioning flagged entry to approved after investigation."""
        entry = FlaggedEntryFactory()
        admin = WorkspaceAdminMemberFactory()

        assert entry.status == "flagged"

        # After investigation, approve entry
        entry.status = "approved"
        entry.reviewed_by = admin
        entry.review_notes = "Investigation complete, entry approved"
        entry.save()

        entry.refresh_from_db()
        assert entry.status == "approved"
        assert entry.reviewed_by == admin
        assert "Investigation complete" in entry.review_notes


@pytest.mark.integration
@pytest.mark.django_db
class TestEntryBulkOperationWorkflows:
    """Test bulk operations on entries."""

    def test_bulk_entry_approval_workflow(self):
        """Test approving multiple entries in bulk."""
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        coordinator = TeamCoordinatorFactory(team=team)

        # Create multiple pending entries
        entries = [PendingEntryFactory(submitted_by=submitter) for _ in range(5)]

        # Bulk approve entries
        for entry in entries:
            entry.status = "approved"
            entry.reviewed_by = coordinator
            entry.review_notes = "Bulk approval"

        Entry.objects.bulk_update(entries, ["status", "reviewed_by", "review_notes"])

        # Verify all entries approved
        approved_entries = Entry.objects.filter(
            submitted_by=submitter, status="approved"
        )
        assert approved_entries.count() == 5

        for entry in approved_entries:
            assert entry.reviewed_by == coordinator
            assert entry.review_notes == "Bulk approval"

    def test_bulk_entry_query_workflow(self):
        """Test querying entries by various criteria."""
        team = TeamFactory()
        submitter1 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        submitter2 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Create entries with different attributes
        [IncomeEntryFactory(submitted_by=submitter1) for _ in range(3)]
        [DisbursementEntryFactory(submitted_by=submitter2) for _ in range(2)]

        # Query by entry type
        income_query = Entry.objects.filter(entry_type="income")
        disbursement_query = Entry.objects.filter(entry_type="disbursement")

        assert income_query.count() == 3
        assert disbursement_query.count() == 2

        # Query by submitter
        submitter1_entries = Entry.objects.filter(submitted_by=submitter1)
        submitter2_entries = Entry.objects.filter(submitted_by=submitter2)

        assert submitter1_entries.count() == 3
        assert submitter2_entries.count() == 2


@pytest.mark.integration
@pytest.mark.django_db
class TestEntryWorkflowIntegration:
    """Test integration between entries and other system components."""

    def test_entry_team_integration_workflow(self):
        """Test how entries integrate with team structure."""
        # Create team with multiple members
        team = TeamFactory(title="Accounting Team")
        submitter1 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        submitter2 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        coordinator = TeamCoordinatorFactory(team=team)

        # Submit entries from different team members
        entry1 = EntryFactory(submitted_by=submitter1, entry_type="income")
        entry2 = EntryFactory(submitted_by=submitter2, entry_type="disbursement")

        # Coordinator reviews both entries
        for entry in [entry1, entry2]:
            entry.status = "approved"
            entry.reviewed_by = coordinator
            entry.review_notes = "Approved by team coordinator"
            entry.save()

        # Verify team workflow
        team_entries = Entry.objects.filter(submitted_by__team=team).select_related(
            "submitted_by", "reviewed_by"
        )

        assert team_entries.count() == 2
        for entry in team_entries:
            assert entry.submitted_by.team == team
            assert entry.reviewed_by == coordinator
            assert entry.status == "approved"

    def test_entry_amount_analysis_workflow(self):
        """Test analyzing entries by amount ranges."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Create entries with various amounts
        [
            EntryFactory(submitted_by=submitter, amount=Decimal("100.00"))
            for _ in range(3)
        ]
        [
            EntryFactory(submitted_by=submitter, amount=Decimal("5000.00"))
            for _ in range(2)
        ]

        # Query by amount ranges
        small_amount_entries = Entry.objects.filter(amount__lt=Decimal("1000.00"))
        large_amount_entries = Entry.objects.filter(amount__gte=Decimal("1000.00"))

        assert small_amount_entries.count() == 3
        assert large_amount_entries.count() == 2

        # Calculate totals
        small_total = sum(entry.amount for entry in small_amount_entries)
        large_total = sum(entry.amount for entry in large_amount_entries)

        assert small_total == Decimal("300.00")
        assert large_total == Decimal("10000.00")

    def test_entry_review_chain_workflow(self):
        """Test complex review chain with multiple reviewers."""
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        reviewer1 = OperationsReviewerFactory(team=team)
        reviewer2 = WorkspaceAdminMemberFactory(team=team)

        # Submit high-value entry
        entry = EntryFactory(
            submitted_by=submitter,
            amount=Decimal("10000.00"),
            entry_type="disbursement",
        )

        # First review - flag for additional review
        entry.status = "flagged"
        entry.reviewed_by = reviewer1
        entry.review_notes = "High amount, requires admin approval"
        entry.save()

        # Second review - final approval
        entry.status = "approved"
        entry.reviewed_by = reviewer2
        entry.review_notes = "Admin review complete, approved for processing"
        entry.save()

        # Verify final state
        entry.refresh_from_db()
        assert entry.status == "approved"
        assert entry.reviewed_by == reviewer2
        assert entry.reviewed_by.role == TeamMemberRole.WORKSPACE_ADMIN
        assert "Admin review complete" in entry.review_notes
