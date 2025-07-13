"""
Unit tests for Entry selector functions.

Tests the selector functions in apps/entries/selectors.py
"""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.entries.constants import EntryStatus, EntryType
from apps.entries.selectors import (
    get_user_workspace_entries,
    get_workspace_entries,
    get_workspace_entries_by_date_range,
    get_workspace_entries_by_status,
    get_workspace_entries_by_type,
    get_workspace_team_entries,
)
from apps.teams.constants import TeamMemberRole
from tests.factories import (
    EntryFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    TeamFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestWorkspaceEntrySelectors:
    """Test selectors for workspace entries."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)

        # Create org member, team, and team member
        self.org_member = OrganizationMemberFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)

        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )

        self.submitter = TeamMemberFactory(
            team=self.team,
            organization_member=self.org_member,
            role=TeamMemberRole.SUBMITTER,
        )

        # Create entries with different statuses
        self.pending_entry = EntryFactory(
            submitter=self.submitter,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_type=EntryType.INCOME,
            status=EntryStatus.PENDING_REVIEW,
            amount=Decimal("100.00"),
        )

        self.approved_entry = EntryFactory(
            submitter=self.submitter,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_type=EntryType.DISBURSEMENT,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00"),
        )

        self.rejected_entry = EntryFactory(
            submitter=self.submitter,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_type=EntryType.REMITTANCE,
            status=EntryStatus.REJECTED,
            amount=Decimal("300.00"),
        )

    def test_get_workspace_entries(self):
        """Test retrieving all entries for a workspace."""
        entries = get_workspace_entries(workspace=self.workspace)

        assert entries.count() == 3
        assert self.pending_entry in entries
        assert self.approved_entry in entries
        assert self.rejected_entry in entries

    def test_get_workspace_entries_by_status(self):
        """Test retrieving entries filtered by status."""
        approved_entries = get_workspace_entries_by_status(
            workspace=self.workspace, status=EntryStatus.APPROVED
        )

        assert approved_entries.count() == 1
        assert self.approved_entry in approved_entries

    def test_get_workspace_entries_by_type(self):
        """Test retrieving entries filtered by type."""
        income_entries = get_workspace_entries_by_type(
            workspace=self.workspace, entry_type=EntryType.INCOME
        )

        assert income_entries.count() == 1
        assert self.pending_entry in income_entries

    def test_get_workspace_entries_by_date_range(self):
        """Test retrieving entries within a date range."""
        today = timezone.now().date()
        tomorrow = today + datetime.timedelta(days=1)
        yesterday = today - datetime.timedelta(days=2)

        # Create an entry with a past date
        old_entry = EntryFactory(
            submitter=self.submitter,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_type=EntryType.INCOME,
            status=EntryStatus.PENDING_REVIEW,
            amount=Decimal("400.00"),
        )

        # Manually set the created_at to yesterday
        old_entry.created_at = timezone.datetime.combine(
            yesterday, timezone.datetime.min.time()
        ).replace(tzinfo=timezone.get_current_timezone())
        old_entry.save(update_fields=["created_at"])

        entries = get_workspace_entries_by_date_range(
            workspace=self.workspace,
            start_date=today,
            end_date=tomorrow,
        )

        assert entries.count() >= 3  # At least our original 3 entries
        assert self.pending_entry in entries
        assert self.approved_entry in entries
        assert self.rejected_entry in entries
        assert old_entry not in entries

    def test_get_user_workspace_entries(self):
        """Test retrieving entries for a specific user in a workspace."""
        # Create another submitter and entry
        other_member = OrganizationMemberFactory(organization=self.organization)
        other_team_member = TeamMemberFactory(
            organization_member=other_member,
            team=self.team,
            role=TeamMemberRole.SUBMITTER,
        )

        # Create an entry by the other member
        other_entry = EntryFactory(
            submitter=other_team_member,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_type=EntryType.INCOME,
            status=EntryStatus.PENDING_REVIEW,
            amount=Decimal("150.00"),
        )

        # First user should only see their entries
        entries = get_user_workspace_entries(
            user=self.org_member.user,
            workspace=self.workspace,
        )

        assert entries.count() == 3
        assert self.pending_entry in entries
        assert self.approved_entry in entries
        assert self.rejected_entry in entries
        assert other_entry not in entries

        # Other user should only see their entry
        other_entries = get_user_workspace_entries(
            user=other_member.user,
            workspace=self.workspace,
        )

        assert other_entries.count() == 1
        assert other_entry in other_entries
        assert self.pending_entry not in other_entries

        # Test filtering by status
        pending_entries = get_user_workspace_entries(
            user=self.org_member.user,
            workspace=self.workspace,
            status=EntryStatus.PENDING_REVIEW,
        )

        assert pending_entries.count() == 1
        assert self.pending_entry in pending_entries

    def test_get_workspace_team_entries(self):
        """Test retrieving entries for a specific workspace team."""
        entries = get_workspace_team_entries(workspace_team=self.workspace_team)

        assert entries.count() == 3
        assert self.pending_entry in entries
        assert self.approved_entry in entries
        assert self.rejected_entry in entries

        # Test filtering by status
        approved_entries = get_workspace_team_entries(
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert approved_entries.count() == 1
        assert self.approved_entry in approved_entries

        # Test filtering by entry type
        income_entries = get_workspace_team_entries(
            workspace_team=self.workspace_team,
            entry_type=EntryType.INCOME,
        )

        assert income_entries.count() == 1
        assert self.pending_entry in income_entries
