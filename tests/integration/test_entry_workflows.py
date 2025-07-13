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
from apps.entries.constants import EntryStatus, EntryType
from tests.factories import (
    DisbursementEntryFactory,
    EntryFactory,
    FlaggedEntryFactory,
    IncomeEntryFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    PendingEntryFactory,
    RemittanceEntryFactory,
    TeamFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.fixture
def org_with_workspace_reviewer():
    """Create organization with workspace and operation_reviewer setup."""
    org = OrganizationFactory()
    workspace = WorkspaceFactory(organization=org)
    reviewer = OrganizationMemberFactory(organization=org)
    workspace.operation_reviewer = reviewer
    workspace.save()
    return {"organization": org, "workspace": workspace, "reviewer": reviewer}


@pytest.fixture
def team_with_workspace(org_with_workspace_reviewer):
    """Create team with workspace and workspace_team setup."""
    org = org_with_workspace_reviewer["organization"]
    workspace = org_with_workspace_reviewer["workspace"]
    reviewer = org_with_workspace_reviewer["reviewer"]

    team = TeamFactory(organization=org)
    workspace_team = WorkspaceTeamFactory(workspace=workspace, team=team)

    return {
        "organization": org,
        "team": team,
        "workspace": workspace,
        "workspace_team": workspace_team,
        "reviewer": reviewer,
    }


@pytest.mark.integration
@pytest.mark.django_db
class TestEntrySubmissionWorkflows:
    """Test entry submission workflows."""

    def test_complete_entry_submission_workflow(self):
        """Test complete entry submission by team member."""
        # Create organization and fundraising team with field agent
        org = OrganizationFactory()
        team = TeamFactory(organization=org, title="Regional Fundraising Team")
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
        assert entry.status == EntryStatus.PENDING_REVIEW
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
            submitter_content_type=team_member_ct, submitter_object_id=submitter.pk
        )
        assert entries.count() == 3

        entry_types = [entry.entry_type for entry in entries]
        assert EntryType.INCOME in entry_types
        assert EntryType.DISBURSEMENT in entry_types
        assert EntryType.REMITTANCE in entry_types

    def test_entry_submission_validation_workflow(self):
        """Test entry submission validation rules."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Create workspace and workspace_team directly
        workspace = WorkspaceFactory()
        workspace_team = WorkspaceTeamFactory(team=submitter.team, workspace=workspace)

        valid_entry = EntryFactory(
            submitter=submitter,
            entry_type=EntryType.INCOME,
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

    def test_complete_entry_approval_workflow(self, team_with_workspace):
        """Test complete entry review and approval process."""
        team = team_with_workspace["team"]
        reviewer = team_with_workspace["reviewer"]

        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Submit entry - ensure it's an income entry type, not workspace_exp
        entry = PendingEntryFactory(submitter=submitter, entry_type=EntryType.INCOME)
        assert entry.status == EntryStatus.PENDING_REVIEW

        # Review and approve entry
        entry.status = EntryStatus.APPROVED
        entry.reviewed_by = reviewer
        entry.review_notes = "Entry looks good, approved for processing"
        entry.save()

        # Verify approval
        entry.refresh_from_db()
        assert entry.status == EntryStatus.APPROVED
        assert entry.reviewed_by == reviewer
        assert entry.review_notes == "Entry looks good, approved for processing"

    def test_entry_rejection_workflow(self, team_with_workspace):
        """Test entry rejection process."""
        team = team_with_workspace["team"]
        reviewer = team_with_workspace["reviewer"]

        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Submit entry - ensure it's an income entry type
        entry = PendingEntryFactory(submitter=submitter, entry_type=EntryType.INCOME)

        # Review and reject entry
        entry.status = EntryStatus.REJECTED
        entry.reviewed_by = reviewer
        entry.review_notes = "Insufficient documentation provided"
        entry.save()

        # Verify rejection
        entry.refresh_from_db()
        assert entry.status == EntryStatus.REJECTED
        assert entry.reviewed_by == reviewer
        assert "Insufficient documentation" in entry.review_notes

    def test_entry_flagging_workflow(self, team_with_workspace):
        """Test entry flagging for further investigation."""
        team = team_with_workspace["team"]
        admin = team_with_workspace["reviewer"]

        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Submit entry - ensure it's an income entry type
        entry = PendingEntryFactory(
            submitter=submitter, amount=Decimal("10000.00"), entry_type=EntryType.INCOME
        )

        # Flag entry for investigation
        entry.is_flagged = True
        entry.reviewed_by = admin
        entry.review_notes = "Large amount requires additional verification"
        entry.save()

        # Verify flagging
        entry.refresh_from_db()
        assert entry.is_flagged
        assert entry.reviewed_by == admin
        assert "additional verification" in entry.review_notes

    def test_reviewer_authorization_workflow(self, team_with_workspace):
        """Test that only authorized roles can review entries."""
        team = team_with_workspace["team"]
        workspace = team_with_workspace["workspace"]
        workspace_team = team_with_workspace["workspace_team"]
        reviewer = team_with_workspace["reviewer"]

        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Test the reviewer
        # Ensure it's an income entry type
        entry = PendingEntryFactory(
            submitter=submitter,
            entry_type=EntryType.INCOME,
            workspace=workspace,
            workspace_team=workspace_team,
        )
        entry.reviewed_by = reviewer
        entry.status = EntryStatus.APPROVED
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

    def test_pending_to_approved_workflow(self, org_with_workspace_reviewer):
        """Test transitioning entry from pending to approved."""
        coordinator = org_with_workspace_reviewer["reviewer"]

        entry = PendingEntryFactory()
        assert entry.status == EntryStatus.PENDING_REVIEW

        # Approve entry
        entry.status = EntryStatus.APPROVED
        entry.reviewed_by = coordinator
        entry.review_notes = "Approved after review"
        entry.save()

        entry.refresh_from_db()
        assert entry.status == EntryStatus.APPROVED
        assert entry.reviewed_by == coordinator

    def test_pending_to_rejected_workflow(self, org_with_workspace_reviewer):
        """Test transitioning entry from pending to rejected."""
        reviewer = org_with_workspace_reviewer["reviewer"]

        entry = PendingEntryFactory()
        assert entry.status == EntryStatus.PENDING_REVIEW

        # Reject entry
        entry.status = EntryStatus.REJECTED
        entry.reviewed_by = reviewer
        entry.review_notes = "Missing required information"
        entry.save()

        entry.refresh_from_db()
        assert entry.status == EntryStatus.REJECTED
        assert entry.reviewed_by == reviewer

    def test_flagged_to_approved_workflow(self, org_with_workspace_reviewer):
        """Test transitioning flagged entry to approved after investigation."""
        admin = org_with_workspace_reviewer["reviewer"]

        entry = FlaggedEntryFactory()
        entry.reviewed_by = admin
        entry.save()

        assert entry.is_flagged

        # After investigation, approve entry
        entry.status = EntryStatus.APPROVED
        entry.review_notes = "Investigation complete, entry approved"
        entry.save()

        entry.refresh_from_db()
        assert entry.status == EntryStatus.APPROVED
        assert entry.reviewed_by == admin
        assert "Investigation complete" in entry.review_notes


@pytest.mark.integration
@pytest.mark.django_db
class TestEntryBulkOperationWorkflows:
    """Test bulk operations on entries."""

    def test_bulk_entry_approval_workflow(self, team_with_workspace):
        """Test approving multiple entries in bulk."""
        team = team_with_workspace["team"]
        coordinator = team_with_workspace["reviewer"]

        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Create multiple pending entries
        entries = [PendingEntryFactory(submitter=submitter) for _ in range(5)]

        # Bulk approve entries
        for entry in entries:
            entry.status = EntryStatus.APPROVED
            entry.reviewed_by = coordinator
            entry.review_notes = "Bulk approval"

        Entry.objects.bulk_update(entries, ["status", "reviewed_by", "review_notes"])

        # Get content type for TeamMember model (not factory)
        team_member_ct = ContentType.objects.get_for_model(TeamMember)

        # Verify all entries approved
        approved_entries = Entry.objects.filter(
            submitter_content_type=team_member_ct,
            submitter_object_id=submitter.pk,
            status=EntryStatus.APPROVED,
        )
        assert approved_entries.count() == 5

        for entry in approved_entries:
            assert entry.reviewed_by == coordinator
            assert entry.review_notes == "Bulk approval"

    def test_bulk_entry_query_workflow(self, team_with_workspace):
        """Test querying entries by various criteria."""
        team = team_with_workspace["team"]

        submitter1 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        submitter2 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Get content types for TeamMember model (not factory)
        team_member_ct = ContentType.objects.get_for_model(TeamMember)

        # Create entries with different attributes
        [IncomeEntryFactory(submitter=submitter1) for _ in range(3)]
        [DisbursementEntryFactory(submitter=submitter2) for _ in range(2)]

        # Query by entry type
        income_query = Entry.objects.filter(entry_type=EntryType.INCOME)
        disbursement_query = Entry.objects.filter(entry_type=EntryType.DISBURSEMENT)

        assert income_query.count() == 3
        assert disbursement_query.count() == 2

        # Query by submitter using content type and object_id
        submitter1_entries = Entry.objects.filter(
            submitter_content_type=team_member_ct, submitter_object_id=submitter1.pk
        )
        submitter2_entries = Entry.objects.filter(
            submitter_content_type=team_member_ct, submitter_object_id=submitter2.pk
        )

        assert submitter1_entries.count() == 3
        assert submitter2_entries.count() == 2


@pytest.mark.integration
@pytest.mark.django_db
class TestEntryWorkflowIntegration:
    """Test integration between entries and other system components."""

    def test_entry_team_integration_workflow(self, team_with_workspace):
        """Test how entries integrate with team structure."""
        team = team_with_workspace["team"]
        coordinator = team_with_workspace["reviewer"]

        # Update team title
        team.title = "Accounting Team"
        team.save()

        submitter1 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)
        submitter2 = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Submit entries from different team members
        entry1 = EntryFactory(submitter=submitter1, entry_type=EntryType.INCOME)
        entry2 = EntryFactory(submitter=submitter2, entry_type=EntryType.DISBURSEMENT)

        # Coordinator reviews both entries
        for entry in [entry1, entry2]:
            entry.status = EntryStatus.APPROVED
            entry.reviewed_by = coordinator
            entry.review_notes = "Approved by team auditor"
            entry.save()

        # Get content type for TeamMember model (not factory)
        team_member_ct = ContentType.objects.get_for_model(TeamMember)

        # Verify team workflow - using team field on submitter_content_type and submitter_object_id
        team_entries = Entry.objects.filter(
            submitter_content_type=team_member_ct, status=EntryStatus.APPROVED
        ).select_related("reviewed_by")

        # Filter entries by team members that belong to this team
        team_member_ids = team.members.values_list("team_member_id", flat=True)
        team_entries = team_entries.filter(submitter_object_id__in=team_member_ids)

        assert team_entries.count() == 2
        for entry in team_entries:
            assert entry.submitter.team == team
            assert entry.reviewed_by == coordinator
            assert entry.status == EntryStatus.APPROVED

    def test_entry_amount_analysis_workflow(self):
        """Test analyzing entries by amount ranges."""
        submitter = TeamMemberFactory(role=TeamMemberRole.SUBMITTER)

        # Create entries with various amounts
        [EntryFactory(submitter=submitter, amount=Decimal("100.00")) for _ in range(3)]
        [EntryFactory(submitter=submitter, amount=Decimal("5000.00")) for _ in range(2)]

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

    def test_entry_review_chain_workflow(self, team_with_workspace):
        """Test complex review chain with multiple reviewers."""
        team = team_with_workspace["team"]
        org = team_with_workspace["organization"]
        reviewer1 = team_with_workspace["reviewer"]

        submitter = TeamMemberFactory(team=team, role=TeamMemberRole.SUBMITTER)

        # Create second reviewer for the same organization
        reviewer2 = OrganizationMemberFactory(organization=org)

        # Submit high-value entry
        entry = EntryFactory(
            submitter=submitter,
            amount=Decimal("10000.00"),
            entry_type=EntryType.DISBURSEMENT,
        )

        # First review - flag for additional review
        entry.is_flagged = True
        entry.reviewed_by = reviewer1
        entry.review_notes = "High amount, requires admin approval"
        entry.save()

        # Second review - final approval
        entry.is_flagged = False
        entry.status = EntryStatus.APPROVED
        entry.reviewed_by = reviewer2
        entry.review_notes = "Admin review complete, approved for processing"
        entry.save()

        # Verify final state
        entry.refresh_from_db()
        assert entry.status == EntryStatus.APPROVED
        assert entry.reviewed_by == reviewer2
        assert entry.reviewed_by.__class__.__name__ == "OrganizationMember"
        assert "Admin review complete" in entry.review_notes
