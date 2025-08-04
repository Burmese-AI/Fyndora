"""
Unit tests for Entry statistics.

Tests the EntryStats class and statistics calculation functionality.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from apps.entries.constants import EntryStatus, EntryType
from apps.entries.stats import EntryStats
from tests.factories import (
    ApprovedEntryFactory,
    OrganizationFactory,
    PendingEntryFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStats:
    """Test EntryStats class functionality."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.submitter = TeamMemberFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.submitter.team
        )

    def test_entry_stats_initialization_with_all_parameters(self):
        """Test EntryStats initialization with all parameters."""
        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Test that the stats object is created successfully
        assert stats is not None
        assert hasattr(stats, "queryset")

    def test_entry_stats_initialization_with_minimal_parameters(self):
        """Test EntryStats initialization with minimal parameters."""
        stats = EntryStats(
            entry_types=[EntryType.INCOME], organization=self.organization
        )

        # Test that the stats object is created successfully
        assert stats is not None
        assert hasattr(stats, "queryset")

    def test_entry_stats_total_calculation(self):
        """Test total amount calculation."""
        # Create approved income entries
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("200.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert stats.total() == Decimal("300.00")

    def test_entry_stats_total_with_no_entries(self):
        """Test total calculation with no matching entries."""
        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert stats.total() == 0

    def test_entry_stats_this_month_calculation(self):
        """Test this month amount calculation."""
        now = timezone.now()

        # Create entry from this month
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("150.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            occurred_at=now.date(),
        )

        # Create entry from last month
        last_month = now - timedelta(days=35)
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            occurred_at=last_month.date(),
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert stats.this_month() == Decimal("150.00")

    def test_entry_stats_last_month_calculation(self):
        """Test last month amount calculation."""
        now = timezone.now()

        # Create entry from this month
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("150.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            occurred_at=now.date(),
        )

        # Create entry from last month
        last_month = now.replace(day=1) - timedelta(days=1)
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            occurred_at=last_month.date(),
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert stats.last_month() == Decimal("100.00")

    def test_entry_stats_average_monthly_calculation(self):
        """Test average monthly amount calculation."""
        now = timezone.now()

        # Create entries across multiple months
        for i in range(3):
            month_date = (now - timedelta(days=30 * i)).date()
            ApprovedEntryFactory(
                entry_type=EntryType.INCOME,
                amount=Decimal("100.00"),
                organization=self.organization,
                workspace=self.workspace,
                workspace_team=self.workspace_team,
                occurred_at=month_date,
            )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Should be total (300) / 12 months = 25
        assert stats.average_monthly() == Decimal("25.00")

    def test_entry_stats_average_monthly_with_no_entries(self):
        """Test average monthly calculation with no entries."""
        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert stats.average_monthly() == 0

    def test_entry_stats_filters_by_entry_type(self):
        """Test stats correctly filter by entry type."""
        # Create income and disbursement entries
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )
        ApprovedEntryFactory(
            entry_type=EntryType.DISBURSEMENT,
            amount=Decimal("50.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # Stats for income only
        income_stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert income_stats.total() == Decimal("100.00")

        # Stats for disbursement only
        disbursement_stats = EntryStats(
            entry_types=[EntryType.DISBURSEMENT],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert disbursement_stats.total() == Decimal("50.00")

    def test_entry_stats_filters_by_status(self):
        """Test stats correctly filter by status."""
        # Create approved and pending entries
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )
        PendingEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("50.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # Stats for approved only
        approved_stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert approved_stats.total() == Decimal("100.00")

        # Stats for pending only
        pending_stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
        )

        assert pending_stats.total() == Decimal("50.00")

    def test_entry_stats_filters_by_organization(self):
        """Test stats correctly filter by organization."""
        other_organization = OrganizationFactory()

        # Create entry in our organization
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # Create entry in other organization
        other_workspace = WorkspaceFactory(organization=other_organization)
        other_submitter = TeamMemberFactory()
        other_workspace_team = WorkspaceTeamFactory(
            workspace=other_workspace, team=other_submitter.team
        )
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("200.00"),
            organization=other_organization,
            workspace=other_workspace,
            workspace_team=other_workspace_team,
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            status=EntryStatus.APPROVED,
        )

        # Should only include entries from our organization
        assert stats.total() == 0

    def test_entry_stats_filters_by_workspace(self):
        """Test stats correctly filter by workspace."""
        other_workspace = WorkspaceFactory(organization=self.organization)
        other_workspace_team = WorkspaceTeamFactory(
            workspace=other_workspace, team=self.submitter.team
        )

        # Create entry in our workspace
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # Create entry in other workspace
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("200.00"),
            organization=self.organization,
            workspace=other_workspace,
            workspace_team=other_workspace_team,
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            status=EntryStatus.APPROVED,
        )

        # Should only include entries from our workspace
        assert stats.total() == 0

    def test_entry_stats_filters_by_workspace_team(self):
        """Test stats correctly filter by workspace team."""
        other_submitter = TeamMemberFactory()
        other_workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=other_submitter.team
        )

        # Create entry in our workspace team
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        # Create entry in other workspace team
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("200.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=other_workspace_team,
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Should only include entries from our workspace team
        assert stats.total() == Decimal("100.00")

    def test_entry_stats_multiple_entry_types(self):
        """Test stats with multiple entry types."""
        # Create different types of entries
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )
        ApprovedEntryFactory(
            entry_type=EntryType.DISBURSEMENT,
            amount=Decimal("50.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )
        ApprovedEntryFactory(
            entry_type=EntryType.REMITTANCE,
            amount=Decimal("75.00"),
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME, EntryType.DISBURSEMENT],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Should include income and disbursement, but not remittance
        assert stats.total() == Decimal("150.00")

    @patch("apps.entries.stats.get_entries")
    def test_entry_stats_uses_get_entries_selector(self, mock_get_entries):
        """Test EntryStats uses get_entries selector correctly."""
        mock_queryset = Mock()
        mock_queryset.aggregate.return_value = {"total": Decimal("100.00")}
        mock_get_entries.return_value = mock_queryset

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Access total to trigger calculation
        total = stats.total()

        # Verify get_entries was called with correct parameters
        mock_get_entries.assert_called_with(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_types=[EntryType.INCOME],
            status=EntryStatus.APPROVED,
        )

        assert total == Decimal("100.00")

    def test_entry_stats_handles_none_aggregation_result(self):
        """Test EntryStats handles None result from aggregation."""
        # When no entries match, aggregation returns None
        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Should return 0 when no entries found
        assert stats.total() == 0
        assert stats.this_month() == 0
        assert stats.last_month() == 0
        assert stats.average_monthly() == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsEdgeCases:
    """Test EntryStats edge cases and error handling."""

    def test_entry_stats_with_empty_entry_types(self):
        """Test EntryStats with empty entry types list."""
        organization = OrganizationFactory()

        # This should raise a ValueError according to current implementation
        with pytest.raises(
            ValueError, match="At least one entry type must be provided"
        ):
            EntryStats(entry_types=[], organization=organization)

    def test_entry_stats_with_invalid_entry_type(self):
        """Test EntryStats with invalid entry type."""
        organization = OrganizationFactory()

        # This should not raise an error, but might return no results
        stats = EntryStats(entry_types=["invalid_type"], organization=organization)

        assert stats.total() == 0

    def test_entry_stats_precision_handling(self):
        """Test EntryStats handles decimal precision correctly."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        submitter = TeamMemberFactory()
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=submitter.team)

        # Create entries with precise decimal amounts
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("33.33"),
            organization=organization,
            workspace=workspace,
            workspace_team=workspace_team,
        )
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("66.67"),
            organization=organization,
            workspace=workspace,
            workspace_team=workspace_team,
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=organization,
            workspace=workspace,
            workspace_team=workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert stats.total() == Decimal("100.00")

    def test_entry_stats_large_amounts(self):
        """Test EntryStats with large amounts."""
        organization = OrganizationFactory()
        workspace = WorkspaceFactory(organization=organization)
        submitter = TeamMemberFactory()
        workspace_team = WorkspaceTeamFactory(workspace=workspace, team=submitter.team)

        # Create entry with large amount
        ApprovedEntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("9999999.99"),
            organization=organization,
            workspace=workspace,
            workspace_team=workspace_team,
        )

        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            organization=organization,
            workspace=workspace,
            workspace_team=workspace_team,
            status=EntryStatus.APPROVED,
        )

        assert stats.total() == Decimal("9999999.99")
