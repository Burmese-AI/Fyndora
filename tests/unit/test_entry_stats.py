"""
Unit tests for Entry stats.

Tests the EntryStats class that provides statistical calculations for entries.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from apps.entries.constants import EntryStatus, EntryType
from apps.entries.stats import EntryStats
from tests.factories import (
    EntryFactory,
    OrganizationWithOwnerFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsInitialization:
    """Test EntryStats initialization and basic setup."""

    def test_entry_stats_initialization_with_organization(self):
        """Test EntryStats initialization with organization."""
        organization = OrganizationWithOwnerFactory()
        # Create a matching approved entry so queryset is not empty
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("10.00"),
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=organization,
            status=EntryStatus.APPROVED
        )
        
        assert stats.queryset is not None
        # Verify the queryset is filtered by organization
        assert stats.queryset.filter(organization=organization).exists()

    def test_entry_stats_initialization_with_workspace(self):
        """Test EntryStats initialization with workspace."""
        workspace = WorkspaceFactory()
        # Create a matching approved entry in this workspace
        EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            organization=workspace.organization,
            workspace=workspace,
            status=EntryStatus.APPROVED,
            amount=Decimal("10.00"),
        )
        
        stats = EntryStats(
            entry_types=[EntryType.WORKSPACE_EXP],
            workspace=workspace,
            status=EntryStatus.APPROVED
        )
        
        assert stats.queryset is not None
        # Verify the queryset is filtered by workspace
        assert stats.queryset.filter(workspace=workspace).exists()

    def test_entry_stats_initialization_with_workspace_team(self):
        """Test EntryStats initialization with workspace team."""
        workspace_team = WorkspaceTeamFactory()
        # Create a matching approved entry for this team
        EntryFactory(
            entry_type=EntryType.INCOME,
            organization=workspace_team.workspace.organization,
            workspace=workspace_team.workspace,
            workspace_team=workspace_team,
            status=EntryStatus.APPROVED,
            amount=Decimal("10.00"),
        )
        
        stats = EntryStats(
            entry_types=[EntryType.INCOME, EntryType.DISBURSEMENT],
            workspace_team=workspace_team,
            status=EntryStatus.APPROVED
        )
        
        assert stats.queryset is not None
        # Verify the queryset is filtered by workspace team
        assert stats.queryset.filter(workspace_team=workspace_team).exists()

    def test_entry_stats_initialization_with_multiple_entry_types(self):
        """Test EntryStats initialization with multiple entry types."""
        organization = OrganizationWithOwnerFactory()
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP, EntryType.WORKSPACE_EXP],
            organization=organization,
            status=EntryStatus.APPROVED
        )
        
        assert stats.queryset is not None

    def test_entry_stats_initialization_without_entry_types(self):
        """Test EntryStats initialization without entry types raises error."""
        organization = OrganizationWithOwnerFactory()
        
        with pytest.raises(ValueError, match="At least one entry type must be provided"):
            EntryStats(
                entry_types=[],
                organization=organization,
                status=EntryStatus.APPROVED
            )

    def test_entry_stats_initialization_with_none_entry_types(self):
        """Test EntryStats initialization with None entry types raises error."""
        organization = OrganizationWithOwnerFactory()
        
        with pytest.raises(ValueError, match="At least one entry type must be provided"):
            EntryStats(
                entry_types=None,
                organization=organization,
                status=EntryStatus.APPROVED
            )

    def test_entry_stats_initialization_with_different_status(self):
        """Test EntryStats initialization with different status."""
        organization = OrganizationWithOwnerFactory()
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=organization,
            status=EntryStatus.PENDING
        )
        
        assert stats.queryset is not None


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsTotal:
    """Test EntryStats total method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()

    def test_total_with_no_entries(self):
        """Test total calculation with no entries."""
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        total = stats.total()
        assert total == 0

    def test_total_with_single_entry(self):
        """Test total calculation with single entry."""
        # Create an approved entry
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        total = stats.total()
        assert total == Decimal("100.00")

    def test_total_with_multiple_entries(self):
        """Test total calculation with multiple entries."""
        # Create multiple approved entries
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00")
        )
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("300.00")
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        total = stats.total()
        assert total == Decimal("600.00")

    def test_total_excludes_pending_entries(self):
        """Test total calculation excludes pending entries."""
        # Create approved entry
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        
        # Create pending entry (should be excluded)
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.PENDING,
            amount=Decimal("200.00")
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        total = stats.total()
        assert total == Decimal("100.00")

    def test_total_with_different_entry_types(self):
        """Test total calculation with different entry types."""
        # Create entries with different types
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00")
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP, EntryType.WORKSPACE_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        total = stats.total()
        assert total == Decimal("300.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsThisMonth:
    """Test EntryStats this_month method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()

    def test_this_month_with_no_entries(self):
        """Test this_month calculation with no entries."""
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        this_month = stats.this_month()
        assert this_month == 0

    def test_this_month_with_current_month_entries(self):
        """Test this_month calculation with current month entries."""
        today = timezone.now().date()
        
        # Create entry for current month
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00"),
            occurred_at=today
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        this_month = stats.this_month()
        assert this_month == Decimal("100.00")

    def test_this_month_excludes_previous_month_entries(self):
        """Test this_month calculation excludes previous month entries."""
        today = timezone.now().date()
        last_month = today - timedelta(days=32)  # Go back more than a month
        
        # Create entry for current month
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00"),
            occurred_at=today
        )
        
        # Create entry for last month (should be excluded)
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00"),
            occurred_at=last_month
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        this_month = stats.this_month()
        assert this_month == Decimal("100.00")

    def test_this_month_with_multiple_current_month_entries(self):
        """Test this_month calculation with multiple current month entries."""
        today = timezone.now().date()
        
        # Create multiple entries for current month
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00"),
            occurred_at=today
        )
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("150.00"),
            occurred_at=today
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        this_month = stats.this_month()
        assert this_month == Decimal("250.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsLastMonth:
    """Test EntryStats last_month method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()

    def test_last_month_with_no_entries(self):
        """Test last_month calculation with no entries."""
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        last_month = stats.last_month()
        assert last_month == 0

    def test_last_month_with_last_month_entries(self):
        """Test last_month calculation with last month entries."""
        today = timezone.now().date()
        last_month_date = today - timedelta(days=32)  # Go back more than a month
        
        # Create entry for last month
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00"),
            occurred_at=last_month_date
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        last_month = stats.last_month()
        assert last_month == Decimal("100.00")

    def test_last_month_excludes_current_month_entries(self):
        """Test last_month calculation excludes current month entries."""
        today = timezone.now().date()
        last_month_date = today - timedelta(days=32)
        
        # Create entry for current month (should be excluded)
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00"),
            occurred_at=today
        )
        
        # Create entry for last month
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00"),
            occurred_at=last_month_date
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        last_month = stats.last_month()
        assert last_month == Decimal("200.00")

    def test_last_month_with_multiple_last_month_entries(self):
        """Test last_month calculation with multiple last month entries."""
        today = timezone.now().date()
        last_month_date = today - timedelta(days=32)
        
        # Create multiple entries for last month
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00"),
            occurred_at=last_month_date
        )
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("150.00"),
            occurred_at=last_month_date
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        last_month = stats.last_month()
        assert last_month == Decimal("250.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsAverageMonthly:
    """Test EntryStats average_monthly method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()

    def test_average_monthly_with_no_entries(self):
        """Test average_monthly calculation with no entries."""
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        average = stats.average_monthly()
        assert average == 0

    def test_average_monthly_with_entries_within_year(self):
        """Test average_monthly calculation with entries within the past year."""
        today = timezone.now().date()
        six_months_ago = today - timedelta(days=180)
        
        # Create entry from 6 months ago
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("1200.00"),  # 1200 / 12 = 100 per month
            occurred_at=six_months_ago
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        average = stats.average_monthly()
        assert average == Decimal("100.00")

    def test_average_monthly_excludes_entries_older_than_year(self):
        """Test average_monthly calculation excludes entries older than a year."""
        today = timezone.now().date()
        six_months_ago = today - timedelta(days=180)
        two_years_ago = today - timedelta(days=730)
        
        # Create entry from 6 months ago (should be included)
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("1200.00"),
            occurred_at=six_months_ago
        )
        
        # Create entry from 2 years ago (should be excluded)
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("2400.00"),
            occurred_at=two_years_ago
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        average = stats.average_monthly()
        assert average == Decimal("100.00")  # Only 1200 / 12

    def test_average_monthly_with_multiple_entries(self):
        """Test average_monthly calculation with multiple entries."""
        today = timezone.now().date()
        three_months_ago = today - timedelta(days=90)
        six_months_ago = today - timedelta(days=180)
        
        # Create multiple entries within the past year
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("600.00"),
            occurred_at=three_months_ago
        )
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("600.00"),
            occurred_at=six_months_ago
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        average = stats.average_monthly()
        assert average == Decimal("100.00")  # (600 + 600) / 12


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsToDict:
    """Test EntryStats to_dict method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()

    def test_to_dict_with_no_entries(self):
        """Test to_dict with no entries."""
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        result = stats.to_dict()
        
        expected = {
            "total": 0,
            "this_month": 0,
            "last_month": 0,
            "average_monthly": 0,
        }
        
        assert result == expected

    def test_to_dict_with_entries(self):
        """Test to_dict with entries."""
        today = timezone.now().date()
        
        # Create entries for different time periods
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00"),
            occurred_at=today
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        result = stats.to_dict()
        
        assert "total" in result
        assert "this_month" in result
        assert "last_month" in result
        assert "average_monthly" in result
        
        assert result["total"] == Decimal("100.00")
        assert result["this_month"] == Decimal("100.00")
        assert result["last_month"] == 0
        # Exact Decimal division per implementation (no rounding)
        assert result["average_monthly"] == (Decimal("100.00") / Decimal(12))


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsAggregateTotal:
    """Test EntryStats _aggregate_total private method."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()

    def test_aggregate_total_with_empty_queryset(self):
        """Test _aggregate_total with empty queryset."""
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        # Use an empty queryset
        empty_queryset = stats.queryset.none()
        total = stats._aggregate_total(empty_queryset)
        
        assert total == 0

    def test_aggregate_total_with_queryset_with_none_amounts(self):
        """Test _aggregate_total handles None amounts correctly."""
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        # Mock a queryset that returns None for aggregate
        mock_queryset = Mock()
        mock_queryset.aggregate.return_value = {"total": None}
        
        total = stats._aggregate_total(mock_queryset)
        
        assert total == 0

    def test_aggregate_total_with_valid_queryset(self):
        """Test _aggregate_total with valid queryset."""
        # Create entries
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00")
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        total = stats._aggregate_total(stats.queryset)
        
        assert total == Decimal("300.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryStatsIntegration:
    """Integration tests for EntryStats."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(workspace=self.workspace)

    def test_entry_stats_with_workspace_context(self):
        """Test EntryStats with workspace context."""
        # Create entries in different contexts
        EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            organization=self.organization,
            workspace=self.workspace,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        
        # Create entry in different workspace (should be excluded)
        other_workspace = WorkspaceFactory(organization=self.organization)
        EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            organization=self.organization,
            workspace=other_workspace,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00")
        )
        
        stats = EntryStats(
            entry_types=[EntryType.WORKSPACE_EXP],
            workspace=self.workspace,
            status=EntryStatus.APPROVED
        )
        
        total = stats.total()
        assert total == Decimal("100.00")

    def test_entry_stats_with_workspace_team_context(self):
        """Test EntryStats with workspace team context."""
        # Create entries in different contexts
        EntryFactory(
            entry_type=EntryType.INCOME,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        
        # Create entry in different workspace team (should be excluded)
        other_workspace_team = WorkspaceTeamFactory(workspace=self.workspace)
        EntryFactory(
            entry_type=EntryType.INCOME,
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=other_workspace_team,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00")
        )
        
        stats = EntryStats(
            entry_types=[EntryType.INCOME],
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        total = stats.total()
        assert total == Decimal("100.00")

    def test_entry_stats_with_multiple_entry_types_and_contexts(self):
        """Test EntryStats with multiple entry types and contexts."""
        # Create entries with different types in the same organization
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            organization=self.organization,
            workspace=self.workspace,
            status=EntryStatus.APPROVED,
            amount=Decimal("200.00")
        )
        
        stats = EntryStats(
            entry_types=[EntryType.ORG_EXP, EntryType.WORKSPACE_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        
        total = stats.total()
        assert total == Decimal("300.00")

    def test_entry_stats_with_different_statuses(self):
        """Test EntryStats with different statuses."""
        # Create entries with different statuses
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.APPROVED,
            amount=Decimal("100.00")
        )
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.PENDING,
            amount=Decimal("200.00")
        )
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            status=EntryStatus.REJECTED,
            amount=Decimal("300.00")
        )
        
        # Test with approved status
        approved_stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.APPROVED
        )
        assert approved_stats.total() == Decimal("100.00")
        
        # Test with pending status
        pending_stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.PENDING
        )
        assert pending_stats.total() == Decimal("200.00")
        
        # Test with rejected status
        rejected_stats = EntryStats(
            entry_types=[EntryType.ORG_EXP],
            organization=self.organization,
            status=EntryStatus.REJECTED
        )
        assert rejected_stats.total() == Decimal("300.00")
