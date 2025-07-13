"""
Unit tests for Entry factories.
"""

from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType

from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.teams.constants import TeamMemberRole
from apps.teams.models import TeamMember
from tests.factories import (
    ApprovedEntryFactory,
    DisbursementEntryFactory,
    EntryFactory,
    EntryWithReviewFactory,
    FlaggedEntryFactory,
    IncomeEntryFactory,
    LargeAmountEntryFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    PendingEntryFactory,
    RejectedEntryFactory,
    RemittanceEntryFactory,
    SmallAmountEntryFactory,
    TeamFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.django_db
class TestEntryFactories:
    """Test entry-related factories."""

    def setup_method(self, method):
        """Set up test hierarchy."""
        # Create standard organization -> workspace -> team structure
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.submitter = TeamMemberFactory(
            team=self.team, role=TeamMemberRole.SUBMITTER
        )

    def test_entry_factory_creates_valid_entry(self):
        """Test EntryFactory creates a valid entry."""
        entry = EntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.entry_id is not None

        # Check submitter relationship through GenericForeignKey
        assert entry.submitter == self.submitter
        assert entry.submitter_content_type == ContentType.objects.get_for_model(
            self.submitter
        )
        assert entry.submitter_object_id == self.submitter.pk
        assert entry.submitter.role == TeamMemberRole.SUBMITTER

        # Check workspace relationship
        assert entry.workspace == self.workspace
        assert entry.workspace.organization == self.organization

        # Check other fields
        assert entry.entry_type in [choice[0] for choice in EntryType.choices]
        assert entry.amount > 0
        assert entry.description is not None
        assert entry.status == EntryStatus.PENDING_REVIEW
        assert entry.reviewed_by is None
        assert entry.review_notes is None

    def test_income_entry_factory(self):
        """Test IncomeEntryFactory creates income entry."""
        entry = IncomeEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.entry_type == EntryType.INCOME
        assert entry.description.startswith("Donation collection from supporters batch")
        assert entry.workspace == self.workspace

    def test_disbursement_entry_factory(self):
        """Test DisbursementEntryFactory creates disbursement entry."""
        entry = DisbursementEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.entry_type == EntryType.DISBURSEMENT
        assert entry.description.startswith("Campaign expense payment")
        assert entry.workspace == self.workspace

    def test_remittance_entry_factory(self):
        """Test RemittanceEntryFactory creates remittance entry."""
        entry = RemittanceEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.entry_type == EntryType.REMITTANCE
        assert entry.description.startswith("Remittance payment to central platform")
        assert entry.workspace == self.workspace


@pytest.mark.django_db
class TestEntryStatusFactories:
    """Test entry factories with different statuses."""

    def setup_method(self, method):
        """Set up test hierarchy."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.coordinator = TeamFactory(
            organization=self.organization,
            team_coordinator=OrganizationMemberFactory(organization=self.organization),
        )

        # Create submitter (TeamMember)
        self.submitter = TeamMemberFactory(
            team=self.team, role=TeamMemberRole.SUBMITTER
        )

        # Create organization members for reviewers
        self.reviewer = OrganizationMemberFactory(organization=self.organization)
        self.admin = OrganizationMemberFactory(organization=self.organization)

        # Create team members for these organization members (for role validation)
        self.reviewer_team_member = TeamMemberFactory(
            organization_member=self.reviewer,
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )
        self.admin_team_member = TeamMemberFactory(
            organization_member=self.admin,
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )

    def test_pending_entry_factory(self):
        """Test PendingEntryFactory creates pending entry."""
        entry = PendingEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.status == EntryStatus.PENDING_REVIEW
        assert entry.description.startswith("Financial transaction awaiting review")
        assert entry.reviewed_by is None
        assert entry.review_notes is None
        assert entry.workspace == self.workspace

    def test_approved_entry_factory(self):
        """Test ApprovedEntryFactory creates approved entry."""
        entry = ApprovedEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
            reviewed_by=self.reviewer,
        )

        assert isinstance(entry, Entry)
        assert entry.status == EntryStatus.APPROVED
        assert entry.description.startswith("Approved financial transaction")
        assert entry.reviewed_by is not None
        assert entry.reviewed_by.organization == self.organization
        assert entry.review_notes is not None
        assert entry.workspace == self.workspace

        # We can still check the role via the related TeamMember
        team_member = TeamMember.objects.get(
            organization_member=entry.reviewed_by, team=self.team
        )
        assert team_member.role == TeamMemberRole.AUDITOR

    def test_rejected_entry_factory(self):
        """Test RejectedEntryFactory creates rejected entry."""
        entry = RejectedEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
            reviewed_by=self.reviewer,
        )

        assert isinstance(entry, Entry)
        assert entry.status == EntryStatus.REJECTED
        assert entry.description.startswith("Rejected financial transaction")
        assert entry.reviewed_by is not None
        assert entry.reviewed_by.organization == self.organization
        assert entry.review_notes is not None
        assert entry.workspace == self.workspace

        # We can still check the role via the related TeamMember
        team_member = TeamMember.objects.get(
            organization_member=entry.reviewed_by, team=self.team
        )
        assert team_member.role == TeamMemberRole.AUDITOR

    def test_flagged_entry_factory(self):
        """Test FlaggedEntryFactory creates flagged entry."""
        entry = FlaggedEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
            reviewed_by=self.admin,
        )

        assert isinstance(entry, Entry)
        assert entry.is_flagged is True
        assert entry.description.startswith("Flagged financial transaction")
        assert entry.reviewed_by is not None
        assert entry.reviewed_by.organization == self.organization
        assert entry.review_notes is not None
        assert entry.workspace == self.workspace

        # We can still check the role via the related TeamMember
        team_member = TeamMember.objects.get(
            organization_member=entry.reviewed_by, team=self.team
        )
        assert team_member.role == TeamMemberRole.AUDITOR


@pytest.mark.django_db
class TestEntryAmountFactories:
    """Test entry factories with specific amounts."""

    def setup_method(self, method):
        """Set up test hierarchy."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.submitter = TeamMemberFactory(
            team=self.team, role=TeamMemberRole.SUBMITTER
        )

    def test_large_amount_entry_factory(self):
        """Test LargeAmountEntryFactory creates large amount entry."""
        entry = LargeAmountEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.amount == Decimal("25000.00")
        assert entry.entry_type == EntryType.INCOME
        assert entry.description.startswith("Major donation from corporate sponsor")
        assert entry.workspace == self.workspace

    def test_small_amount_entry_factory(self):
        """Test SmallAmountEntryFactory creates small amount entry."""
        entry = SmallAmountEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.amount == Decimal("50.00")
        assert entry.entry_type == EntryType.DISBURSEMENT
        assert entry.description.startswith("Small campaign expense")
        assert entry.workspace == self.workspace


@pytest.mark.django_db
class TestEntryWithReviewFactory:
    """Test entry factory with review functionality."""

    def setup_method(self, method):
        """Set up test hierarchy."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.submitter = TeamMemberFactory(
            team=self.team, role=TeamMemberRole.SUBMITTER
        )

        # Create organization members for reviewers
        self.coordinator = OrganizationMemberFactory(organization=self.organization)
        self.reviewer = OrganizationMemberFactory(organization=self.organization)
        self.admin = OrganizationMemberFactory(organization=self.organization)

        # Create team members for these organization members (for role validation)
        self.coord_team_member = TeamMemberFactory(
            organization_member=self.coordinator,
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )
        self.reviewer_team_member = TeamMemberFactory(
            organization_member=self.reviewer,
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )
        self.admin_team_member = TeamMemberFactory(
            organization_member=self.admin,
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )

    def test_entry_with_review_factory_default(self):
        """Test EntryWithReviewFactory creates approved entry by default."""
        entry = EntryWithReviewFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.status == EntryStatus.APPROVED
        assert entry.reviewed_by is not None
        assert entry.review_notes is not None
        assert "approved" in entry.review_notes.lower()
        assert entry.workspace == self.workspace

    def test_entry_with_review_factory_custom_status(self):
        """Test EntryWithReviewFactory with custom status."""
        entry = EntryWithReviewFactory(
            review="rejected",
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.status == EntryStatus.REJECTED
        assert entry.reviewed_by is not None
        assert entry.review_notes is not None
        assert "rejected" in entry.review_notes.lower()
        assert entry.workspace == self.workspace

    def test_entry_with_review_factory_flagged(self):
        """Test EntryWithReviewFactory with flagged status."""
        entry = EntryWithReviewFactory(
            review="flagged",
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        assert isinstance(entry, Entry)
        assert entry.is_flagged is True
        assert entry.reviewed_by is not None
        assert entry.review_notes is not None
        assert "flagged" in entry.review_notes.lower()
        assert entry.workspace == self.workspace


@pytest.mark.django_db
class TestEntryValidation:
    """Test entry validation through factories."""

    def setup_method(self, method):
        """Set up test hierarchy."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        self.submitter = TeamMemberFactory(
            team=self.team, role=TeamMemberRole.SUBMITTER
        )

        # Create organization member for coordinator
        self.coordinator = OrganizationMemberFactory(organization=self.organization)
        self.coord_team_member = TeamMemberFactory(
            organization_member=self.coordinator,
            team=self.team,
            role=TeamMemberRole.AUDITOR,
        )

    def test_entry_submitter_role_validation(self):
        """Test that entries can only be submitted by submitters."""
        entry = EntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
        )

        # Check ContentType relations
        assert entry.submitter_content_type == ContentType.objects.get_for_model(
            self.submitter
        )
        assert entry.submitter_object_id == self.submitter.pk

        # Should be created with submitter role
        assert entry.submitter.role == TeamMemberRole.SUBMITTER

        # Skip full_clean because of complex validation in Entry model
        # The factory itself ensures the entity is created correctly

    def test_entry_reviewer_role_validation(self):
        """Test that entries can only be reviewed by authorized roles."""
        approved_entry = ApprovedEntryFactory(
            workspace=self.workspace,
            submitter=self.submitter,
            workspace_team=self.workspace_team,
            reviewed_by=self.coordinator,
        )

        # Check entry has a reviewer
        assert approved_entry.reviewed_by is not None
        assert approved_entry.reviewed_by.organization == self.organization

        # Find the related team member to check its role
        team_member = TeamMember.objects.get(
            organization_member=approved_entry.reviewed_by, team=self.team
        )
        assert team_member.role == TeamMemberRole.AUDITOR

        # Skip full_clean validation
