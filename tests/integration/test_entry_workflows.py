"""
Integration tests for Entry workflows.

Tests how entries work with team members, submission, review, and approval processes.
"""

import pytest
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

from apps.entries.models import Entry
from apps.teams.constants import TeamMemberRole
from apps.teams.models import TeamMember
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
    WorkspaceFactory,
    WorkspaceTeamFactory,
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
            submitter=field_agent,
            entry_type="income",
            amount=Decimal("1500.00"),
            description="Weekly donation collections from local supporters",
        )

        # Verify submission
        assert entry.submitter == field_agent
        assert entry.submitter.role == TeamMemberRole.SUBMITTER
        assert entry.submitter.team == team
        assert entry.entry_type == "income"
        assert entry.amount == Decimal("1500.00")
        assert entry.status == "pending_review"
        assert entry.reviewed_by is None
        assert entry.review_notes is None

    def test_multiple_entry_types_submission_workflow(self):
        """Test submitting different types of entries."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)
        
        # Get content type for TeamMember model (not factory)
        team_member_ct = ContentType.objects.get_for_model(TeamMember)

        # Submit different entry types
        IncomeEntryFactory(submitter=submitter, amount=Decimal("2000.00"))
        DisbursementEntryFactory(submitter=submitter, amount=Decimal("500.00"))
        RemittanceEntryFactory(submitter=submitter, amount=Decimal("1800.00"))

        # Verify all entries using content type and object_id
        entries = Entry.objects.filter(
            submitter_content_type=team_member_ct,
            submitter_object_id=submitter.pk
        )
        assert entries.count() == 3

        entry_types = [entry.entry_type for entry in entries]
        assert "income" in entry_types
        assert "disbursement" in entry_types
        assert "remittance" in entry_types

    def test_entry_submission_validation_workflow(self):
        """Test entry submission validation rules."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Create workspace and workspace_team directly
        workspace = WorkspaceFactory()
        workspace_team = WorkspaceTeamFactory(team=submitter.team, workspace=workspace)
            
        valid_entry = EntryFactory(
            submitter=submitter,
            entry_type="income",
            amount=Decimal("100.00"),
            description="Valid entry",
            workspace=workspace,
            workspace_team=workspace_team,
        )

        # Entry should pass validation
        valid_entry.full_clean()
        assert valid_entry.submitter.role == TeamMemberRole.SUBMITTER


@pytest.mark.integration
@pytest.mark.django_db
class TestEntryReviewWorkflows:
    """Test entry review and approval workflows."""

    def test_complete_entry_approval_workflow(self):
        """Test complete entry review and approval process."""
        # Create team with submitter and coordinator
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        team_coordinator = TeamCoordinatorFactory(team=team)
        
        # Get the organization member associated with the coordinator
        coordinator = team_coordinator.organization_member

        # Submit entry - ensure it's an income entry type, not workspace_exp
        entry = PendingEntryFactory(submitter=submitter, entry_type="income")
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
        assert entry.reviewed_by.user == team_coordinator.organization_member.user
        assert entry.review_notes == "Entry looks good, approved for processing"

    def test_entry_rejection_workflow(self):
        """Test entry rejection process."""
        # Create team with submitter and reviewer
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        team_reviewer = OperationsReviewerFactory(team=team)
        
        # Get the organization member associated with the reviewer
        reviewer = team_reviewer.organization_member

        # Submit entry - ensure it's an income entry type
        entry = PendingEntryFactory(submitter=submitter, entry_type="income")

        # Review and reject entry
        entry.status = "rejected"
        entry.reviewed_by = reviewer
        entry.review_notes = "Insufficient documentation provided"
        entry.save()

        # Verify rejection
        entry.refresh_from_db()
        assert entry.status == "rejected"
        assert entry.reviewed_by == reviewer
        assert entry.reviewed_by.user == team_reviewer.organization_member.user
        assert "Insufficient documentation" in entry.review_notes

    def test_entry_flagging_workflow(self):
        """Test entry flagging for further investigation."""
        # Create team with submitter and workspace admin
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        team_admin = WorkspaceAdminMemberFactory(team=team)
        
        # Get the organization member associated with the admin
        admin = team_admin.organization_member

        # Submit entry - ensure it's an income entry type
        entry = PendingEntryFactory(
            submitter=submitter, 
            amount=Decimal("10000.00"),
            entry_type="income"
        )

        # Flag entry for investigation
        entry.status = "flagged"
        entry.reviewed_by = admin
        entry.review_notes = "Large amount requires additional verification"
        entry.save()

        # Verify flagging
        entry.refresh_from_db()
        assert entry.status == "flagged"
        assert entry.reviewed_by == admin
        assert entry.reviewed_by.user == team_admin.organization_member.user
        assert "additional verification" in entry.review_notes

    def test_reviewer_authorization_workflow(self):
        """Test that only authorized roles can review entries."""
        team = TeamFactory()
        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Create reviewers with different authorized roles
        team_coordinator = TeamCoordinatorFactory(team=team)
        team_operations_reviewer = OperationsReviewerFactory(team=team)
        team_workspace_admin = WorkspaceAdminMemberFactory(team=team)
        
        # Get the organization members associated with the team members
        coordinator = team_coordinator.organization_member
        operations_reviewer = team_operations_reviewer.organization_member
        workspace_admin = team_workspace_admin.organization_member

        # Test each reviewer type
        for reviewer in [coordinator, operations_reviewer, workspace_admin]:
            # Ensure it's an income entry type
            entry = PendingEntryFactory(submitter=submitter, entry_type="income")
            entry.reviewed_by = reviewer
            entry.status = "approved"
            entry.review_notes = f"Reviewed by {reviewer.user.email}"

            # Should validate successfully
            entry.full_clean()
            entry.save()

            # Verify the reviewer is an OrganizationMember
            assert entry.reviewed_by.__class__.__name__ == "OrganizationMember"


@pytest.mark.integration
@pytest.mark.django_db
class TestEntryStatusTransitionWorkflows:
    """Test entry status transition workflows."""

    def test_pending_to_approved_workflow(self):
        """Test transitioning entry from pending to approved."""
        entry = PendingEntryFactory()
        team_coordinator = TeamCoordinatorFactory()
        coordinator = team_coordinator.organization_member

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
        team_reviewer = OperationsReviewerFactory()
        reviewer = team_reviewer.organization_member

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
        # Create a flagged entry with proper OrganizationMember as reviewer
        team_admin = WorkspaceAdminMemberFactory()
        admin = team_admin.organization_member
        
        entry = FlaggedEntryFactory()
        entry.reviewed_by = admin
        entry.save()

        assert entry.status == "flagged"

        # After investigation, approve entry
        entry.status = "approved"
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
        team_coordinator = TeamCoordinatorFactory(team=team)
        coordinator = team_coordinator.organization_member

        # Create multiple pending entries
        entries = [PendingEntryFactory(submitter=submitter) for _ in range(5)]

        # Bulk approve entries
        for entry in entries:
            entry.status = "approved"
            entry.reviewed_by = coordinator
            entry.review_notes = "Bulk approval"

        Entry.objects.bulk_update(entries, ["status", "reviewed_by", "review_notes"])

        # Get content type for TeamMember model (not factory)
        team_member_ct = ContentType.objects.get_for_model(TeamMember)
        
        # Verify all entries approved
        approved_entries = Entry.objects.filter(
            submitter_content_type=team_member_ct,
            submitter_object_id=submitter.pk,
            status="approved"
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
        
        # Get content types for TeamMember model (not factory)
        team_member_ct = ContentType.objects.get_for_model(TeamMember)

        # Create entries with different attributes
        [IncomeEntryFactory(submitter=submitter1) for _ in range(3)]
        [DisbursementEntryFactory(submitter=submitter2) for _ in range(2)]

        # Query by entry type
        income_query = Entry.objects.filter(entry_type="income")
        disbursement_query = Entry.objects.filter(entry_type="disbursement")

        assert income_query.count() == 3
        assert disbursement_query.count() == 2

        # Query by submitter using content type and object_id
        submitter1_entries = Entry.objects.filter(
            submitter_content_type=team_member_ct,
            submitter_object_id=submitter1.pk
        )
        submitter2_entries = Entry.objects.filter(
            submitter_content_type=team_member_ct,
            submitter_object_id=submitter2.pk
        )

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
        team_coordinator = TeamCoordinatorFactory(team=team)
        coordinator = team_coordinator.organization_member

        # Submit entries from different team members
        entry1 = EntryFactory(submitter=submitter1, entry_type="income")
        entry2 = EntryFactory(submitter=submitter2, entry_type="disbursement")

        # Coordinator reviews both entries
        for entry in [entry1, entry2]:
            entry.status = "approved"
            entry.reviewed_by = coordinator
            entry.review_notes = "Approved by team coordinator"
            entry.save()

        # Get content type for TeamMember model (not factory)
        team_member_ct = ContentType.objects.get_for_model(TeamMember)
        
        # Verify team workflow - using team field on submitter_content_type and submitter_object_id
        team_entries = Entry.objects.filter(
            submitter_content_type=team_member_ct,
            status="approved"
        ).select_related("reviewed_by")
        
        # Filter entries by team members that belong to this team
        team_member_ids = team.members.values_list('team_member_id', flat=True)
        team_entries = team_entries.filter(submitter_object_id__in=team_member_ids)

        assert team_entries.count() == 2
        for entry in team_entries:
            assert entry.submitter.team == team
            assert entry.reviewed_by == coordinator
            assert entry.status == "approved"

    def test_entry_amount_analysis_workflow(self):
        """Test analyzing entries by amount ranges."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Create entries with various amounts
        [
            EntryFactory(submitter=submitter, amount=Decimal("100.00"))
            for _ in range(3)
        ]
        [
            EntryFactory(submitter=submitter, amount=Decimal("5000.00"))
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
        team_reviewer1 = OperationsReviewerFactory(team=team)
        team_reviewer2 = WorkspaceAdminMemberFactory(team=team)
        
        # Get the organization members
        reviewer1 = team_reviewer1.organization_member
        reviewer2 = team_reviewer2.organization_member

        # Submit high-value entry
        entry = EntryFactory(
            submitter=submitter,
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
        assert entry.reviewed_by.__class__.__name__ == "OrganizationMember"
        assert "Admin review complete" in entry.review_notes
