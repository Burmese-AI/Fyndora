"""Unit tests for Reports selectors.

Tests the selector functions in apps/reports/selectors.py
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from django.db.models.signals import post_save

from apps.remittance.constants import RemittanceStatus
from apps.reports.selectors import EntrySelectors, RemittanceSelectors
from apps.workspaces.models import WorkspaceTeam
from apps.workspaces.signals import create_remittance
from tests.factories import (
    ApprovedEntryFactory,
    EntryFactory,
    OrganizationFactory,
    PendingEntryFactory,
    RejectedEntryFactory,
    RemittanceFactory,
    TeamFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.django_db
class TestRemittanceSelectors:
    """Test RemittanceSelectors class methods."""

    def setup_method(self):
        """Set up test data and disconnect signal."""
        # Disconnect the signal to prevent automatic remittance creation
        post_save.disconnect(create_remittance, sender=WorkspaceTeam)

        self.organization = OrganizationFactory()
        self.other_organization = OrganizationFactory()

        self.workspace1 = WorkspaceFactory(organization=self.organization)
        self.workspace2 = WorkspaceFactory(organization=self.organization)
        self.other_workspace = WorkspaceFactory(organization=self.other_organization)

        self.team1 = TeamFactory(organization=self.organization)
        self.team2 = TeamFactory(organization=self.organization)

        self.workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=self.team1
        )
        self.workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace2, team=self.team2
        )
        self.other_workspace_team = WorkspaceTeamFactory(
            workspace=self.other_workspace,
            team=TeamFactory(organization=self.other_organization),
        )

    def teardown_method(self):
        """Reconnect signal after test."""
        # Reconnect the signal
        post_save.connect(create_remittance, sender=WorkspaceTeam)

    def test_get_total_due_amount_basic(self):
        """Test get_total_due_amount returns correct total."""
        # Create new workspace teams for this test
        due_workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        due_workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace2, team=TeamFactory(organization=self.organization)
        )

        # Create remittances with different due amounts
        RemittanceFactory(
            workspace_team=due_workspace_team1,
            due_amount=Decimal("100.00"),
            status=RemittanceStatus.PENDING,
        )
        RemittanceFactory(
            workspace_team=due_workspace_team2,
            due_amount=Decimal("200.00"),
            status=RemittanceStatus.PARTIAL,
        )

        # Create remittance for other organization (should be excluded)
        other_org_workspace_team = WorkspaceTeamFactory(
            workspace=self.other_workspace,
            team=TeamFactory(organization=self.other_organization),
        )
        RemittanceFactory(
            workspace_team=other_org_workspace_team,
            due_amount=Decimal("500.00"),
            status=RemittanceStatus.PENDING,
        )

        # Create canceled remittance (should be excluded) - use new workspace team
        canceled_workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        RemittanceFactory(
            workspace_team=canceled_workspace_team,
            due_amount=Decimal("300.00"),
            status=RemittanceStatus.CANCELED,
        )

        total = RemittanceSelectors.get_total_due_amount(
            self.organization.organization_id
        )
        assert total == Decimal("300.00")

    def test_get_total_due_amount_with_workspace_filter(self):
        """Test get_total_due_amount with workspace filtering."""
        # Create new workspace teams for this test
        filter_due_workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        filter_due_workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace2, team=TeamFactory(organization=self.organization)
        )

        RemittanceFactory(
            workspace_team=filter_due_workspace_team1,
            due_amount=Decimal("100.00"),
            status=RemittanceStatus.PENDING,
        )
        RemittanceFactory(
            workspace_team=filter_due_workspace_team2,
            due_amount=Decimal("200.00"),
            status=RemittanceStatus.PENDING,
        )

        # Filter by workspace1 only
        total = RemittanceSelectors.get_total_due_amount(
            self.organization.organization_id, workspace_id=self.workspace1.workspace_id
        )
        assert total == Decimal("100.00")

    def test_get_total_due_amount_no_remittances(self):
        """Test get_total_due_amount returns 0 when no remittances exist."""
        total = RemittanceSelectors.get_total_due_amount(
            self.organization.organization_id
        )
        assert total == Decimal("0.00")

    def test_get_total_paid_amount_basic(self):
        """Test get_total_paid_amount returns correct total."""
        # Create new workspace teams for this test
        paid_workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        paid_workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace2, team=TeamFactory(organization=self.organization)
        )

        RemittanceFactory(
            workspace_team=paid_workspace_team1,
            paid_amount=Decimal("50.00"),
            status=RemittanceStatus.PARTIAL,
        )
        RemittanceFactory(
            workspace_team=paid_workspace_team2,
            paid_amount=Decimal("150.00"),
            status=RemittanceStatus.PAID,
        )

        # Canceled remittance (should be excluded)
        canceled_workspace_team_paid = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        RemittanceFactory(
            workspace_team=canceled_workspace_team_paid,
            paid_amount=Decimal("100.00"),
            status=RemittanceStatus.CANCELED,
        )

        total = RemittanceSelectors.get_total_paid_amount(
            self.organization.organization_id
        )
        assert total == Decimal("200.00")

    def test_get_total_paid_amount_with_workspace_filter(self):
        """Test get_total_paid_amount with workspace filtering."""
        # Create new workspace teams for this test
        filter_workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        filter_workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace2, team=TeamFactory(organization=self.organization)
        )

        RemittanceFactory(
            workspace_team=filter_workspace_team1,
            paid_amount=Decimal("50.00"),
            status=RemittanceStatus.PAID,
        )
        RemittanceFactory(
            workspace_team=filter_workspace_team2,
            paid_amount=Decimal("150.00"),
            status=RemittanceStatus.PAID,
        )

        total = RemittanceSelectors.get_total_paid_amount(
            self.organization.organization_id, workspace_id=self.workspace1.workspace_id
        )
        assert total == Decimal("50.00")

    def test_get_overdue_amount_basic(self):
        """Test get_overdue_amount returns correct total."""
        # Create workspaces with past end dates to make them overdue
        past_date = timezone.now().date() - timedelta(days=10)
        overdue_workspace = WorkspaceFactory(
            organization=self.organization, end_date=past_date
        )
        partial_workspace = WorkspaceFactory(
            organization=self.organization, end_date=past_date
        )

        # Create new workspace team for overdue remittance
        overdue_workspace_team = WorkspaceTeamFactory(
            workspace=overdue_workspace,
            team=TeamFactory(organization=self.organization),
        )
        # Create overdue remittances
        RemittanceFactory(
            workspace_team=overdue_workspace_team,
            due_amount=Decimal("100.00"),
            paid_amount=Decimal("0.00"),
            status=RemittanceStatus.OVERDUE,
        )
        # Create new workspace team for partial remittance
        partial_workspace_team = WorkspaceTeamFactory(
            workspace=partial_workspace,
            team=TeamFactory(organization=self.organization),
        )
        RemittanceFactory(
            workspace_team=partial_workspace_team,
            due_amount=Decimal("200.00"),
            paid_amount=Decimal("0.00"),
            status=RemittanceStatus.PARTIAL,
        )

        # Non-overdue remittance (should be excluded) - use workspace with future end date
        future_workspace = WorkspaceFactory(
            organization=self.organization,
            end_date=timezone.now().date() + timedelta(days=10),
        )
        pending_workspace_team = WorkspaceTeamFactory(
            workspace=future_workspace, team=TeamFactory(organization=self.organization)
        )
        RemittanceFactory(
            workspace_team=pending_workspace_team,
            due_amount=Decimal("300.00"),
            paid_amount=Decimal("0.00"),
            status=RemittanceStatus.PENDING,
        )

        total = RemittanceSelectors.get_overdue_amount(
            self.organization.organization_id
        )
        assert total == Decimal("300.00")

    def test_get_overdue_amount_with_end_date(self):
        """Test get_overdue_amount with end_date filtering."""
        past_date = timezone.now().date() - timedelta(days=10)
        future_date = timezone.now().date() + timedelta(days=10)

        # Create workspace with past end_date (overdue)
        past_workspace = WorkspaceFactory(
            organization=self.organization, end_date=past_date
        )
        past_workspace_team = WorkspaceTeamFactory(
            workspace=past_workspace, team=self.team1
        )

        # Create workspace with future end_date (not overdue)
        future_workspace = WorkspaceFactory(
            organization=self.organization, end_date=future_date
        )
        future_workspace_team = WorkspaceTeamFactory(
            workspace=future_workspace, team=self.team2
        )

        RemittanceFactory(
            workspace_team=past_workspace_team,
            due_amount=Decimal("100.00"),
            status=RemittanceStatus.PENDING,
        )
        RemittanceFactory(
            workspace_team=future_workspace_team,
            due_amount=Decimal("200.00"),
            status=RemittanceStatus.PENDING,
        )

        total = RemittanceSelectors.get_overdue_amount(
            self.organization.organization_id
        )
        assert total == Decimal("100.00")

    def test_get_remaining_due_amount(self):
        """Test get_remaining_due_amount calculates correctly."""
        # Create new workspace teams for this test
        remaining_workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        remaining_workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace2, team=TeamFactory(organization=self.organization)
        )

        RemittanceFactory(
            workspace_team=remaining_workspace_team1,
            due_amount=Decimal("100.00"),
            paid_amount=Decimal("30.00"),
            status=RemittanceStatus.PARTIAL,
        )
        RemittanceFactory(
            workspace_team=remaining_workspace_team2,
            due_amount=Decimal("200.00"),
            paid_amount=Decimal("0.00"),
            status=RemittanceStatus.PENDING,
        )

        remaining = RemittanceSelectors.get_remaining_due_amount(
            self.organization.organization_id
        )
        # (100 - 30) + (200 - 0) = 270
        assert remaining == Decimal("270.00")

    def test_get_summary_stats(self):
        """Test get_summary_stats returns all statistics."""
        # Create new workspace teams for this test
        summary_workspace_team1 = WorkspaceTeamFactory(
            workspace=self.workspace1, team=TeamFactory(organization=self.organization)
        )
        summary_workspace_team2 = WorkspaceTeamFactory(
            workspace=self.workspace2, team=TeamFactory(organization=self.organization)
        )

        RemittanceFactory(
            workspace_team=summary_workspace_team1,
            due_amount=Decimal("100.00"),
            paid_amount=Decimal("30.00"),
            status=RemittanceStatus.PARTIAL,
        )
        RemittanceFactory(
            workspace_team=summary_workspace_team2,
            due_amount=Decimal("200.00"),
            paid_amount=Decimal("200.00"),
            status=RemittanceStatus.PAID,
        )

        stats = RemittanceSelectors.get_summary_stats(self.organization.organization_id)

        assert stats["total_due"] == Decimal("300.00")
        assert stats["total_paid"] == Decimal("230.00")
        assert stats["remaining_due"] == Decimal("70.00")
        assert "overdue_amount" in stats


@pytest.mark.django_db
class TestEntrySelectors:
    """Test EntrySelectors class methods."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.other_organization = OrganizationFactory()

        self.workspace1 = WorkspaceFactory(organization=self.organization)
        self.workspace2 = WorkspaceFactory(organization=self.organization)
        self.other_workspace = WorkspaceFactory(organization=self.other_organization)

    def test_get_total_count_basic(self):
        """Test get_total_count returns correct count."""
        # Create entries for the organization
        EntryFactory(organization=self.organization, workspace=self.workspace1)
        EntryFactory(organization=self.organization, workspace=self.workspace2)

        # Create entry for other organization (should be excluded)
        EntryFactory(
            organization=self.other_organization,
            workspace=self.other_workspace,
        )

        count = EntrySelectors.get_total_count(self.organization.organization_id)
        assert count == 2

    def test_get_total_count_with_workspace_filter(self):
        """Test get_total_count with workspace filtering."""
        EntryFactory(organization=self.organization, workspace=self.workspace1)
        EntryFactory(organization=self.organization, workspace=self.workspace2)

        count = EntrySelectors.get_total_count(
            self.organization.organization_id, workspace_id=self.workspace1.workspace_id
        )
        assert count == 1

    def test_get_total_count_no_entries(self):
        """Test get_total_count returns 0 when no entries exist."""
        count = EntrySelectors.get_total_count(self.organization.organization_id)
        assert count == 0

    def test_get_pending_count(self):
        """Test get_pending_count returns correct count."""
        PendingEntryFactory(organization=self.organization, workspace=self.workspace1)
        PendingEntryFactory(organization=self.organization, workspace=self.workspace2)

        # Create approved entry (should be excluded)
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace1)

        count = EntrySelectors.get_pending_count(self.organization.organization_id)
        assert count == 2

    def test_get_pending_count_with_workspace_filter(self):
        """Test get_pending_count with workspace filtering."""
        PendingEntryFactory(organization=self.organization, workspace=self.workspace1)
        PendingEntryFactory(organization=self.organization, workspace=self.workspace2)

        count = EntrySelectors.get_pending_count(
            self.organization.organization_id, workspace_id=self.workspace1.workspace_id
        )
        assert count == 1

    def test_get_approved_count(self):
        """Test get_approved_count returns correct count."""
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace1)
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace2)

        # Create pending entry (should be excluded)
        PendingEntryFactory(organization=self.organization, workspace=self.workspace1)

        count = EntrySelectors.get_approved_count(self.organization.organization_id)
        assert count == 2

    def test_get_approved_count_with_workspace_filter(self):
        """Test get_approved_count with workspace filtering."""
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace1)
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace2)

        count = EntrySelectors.get_approved_count(
            self.organization.organization_id, workspace_id=self.workspace1.workspace_id
        )
        assert count == 1

    def test_get_rejected_count(self):
        """Test get_rejected_count returns correct count."""
        RejectedEntryFactory(organization=self.organization, workspace=self.workspace1)
        RejectedEntryFactory(organization=self.organization, workspace=self.workspace2)

        # Create approved entry (should be excluded)
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace1)

        count = EntrySelectors.get_rejected_count(self.organization.organization_id)
        assert count == 2

    def test_get_rejected_count_with_workspace_filter(self):
        """Test get_rejected_count with workspace filtering."""
        RejectedEntryFactory(organization=self.organization, workspace=self.workspace1)
        RejectedEntryFactory(organization=self.organization, workspace=self.workspace2)

        count = EntrySelectors.get_rejected_count(
            self.organization.organization_id, workspace_id=self.workspace1.workspace_id
        )
        assert count == 1

    def test_get_summary_stats(self):
        """Test get_summary_stats returns all statistics."""
        PendingEntryFactory(organization=self.organization, workspace=self.workspace1)
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace1)
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace2)
        RejectedEntryFactory(organization=self.organization, workspace=self.workspace1)

        stats = EntrySelectors.get_summary_stats(self.organization.organization_id)

        assert stats["total_entries"] == 4
        assert stats["pending_entries"] == 1
        assert stats["approved_entries"] == 2
        assert stats["rejected_entries"] == 1

    def test_get_summary_stats_with_workspace_filter(self):
        """Test get_summary_stats with workspace filtering."""
        PendingEntryFactory(organization=self.organization, workspace=self.workspace1)
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace1)
        ApprovedEntryFactory(organization=self.organization, workspace=self.workspace2)

        stats = EntrySelectors.get_summary_stats(
            self.organization.organization_id, workspace_id=self.workspace1.workspace_id
        )

        assert stats["total_entries"] == 2
        assert stats["pending_entries"] == 1
        assert stats["approved_entries"] == 1
        assert stats["rejected_entries"] == 0
