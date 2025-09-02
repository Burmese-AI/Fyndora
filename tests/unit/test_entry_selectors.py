"""
Unit tests for Entry selectors.

Tests the selector functions that provide data access for entries.
"""

from decimal import Decimal
from typing import List

import pytest
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.test import TestCase

from apps.currencies.models import Currency
from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.entries.selectors import get_entries, get_total_amount_of_entries, get_entry
from tests.factories import (
    EntryFactory,
    IncomeEntryFactory,
    DisbursementEntryFactory,
    RemittanceEntryFactory,
    OrganizationMemberFactory,
    TeamMemberFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
    OrganizationWithOwnerFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestGetEntries:
    """Test the get_entries selector function."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team_member = TeamMemberFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team_member.team
        )
        
        # Create currencies
        self.usd_currency = Currency.objects.get_or_create(code="USD", name="US Dollar")[0]
        self.eur_currency = Currency.objects.get_or_create(code="EUR", name="Euro")[0]

    def test_get_entries_requires_entry_types(self):
        """Test that get_entries raises ValueError when no entry types provided."""
        with pytest.raises(ValueError, match="At least one entry type must be provided"):
            get_entries(entry_types=[])

    def test_get_entries_with_team_entry_types_and_workspace_team(self):
        """Test get_entries filters team entries by workspace team."""
        # Create team entries
        income_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )
        disbursement_entry = DisbursementEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )
        
        # Create entries for different workspace team
        other_workspace_team = WorkspaceTeamFactory()
        IncomeEntryFactory(
            workspace_team=other_workspace_team,
            workspace=other_workspace_team.workspace,
            organization=other_workspace_team.workspace.organization,
            currency=self.usd_currency,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME, EntryType.DISBURSEMENT],
            workspace_team=self.workspace_team,
        )

        assert entries.count() == 2
        entry_ids = [entry.entry_id for entry in entries]
        assert income_entry.entry_id in entry_ids
        assert disbursement_entry.entry_id in entry_ids

    def test_get_entries_with_team_entry_types_and_workspace(self):
        """Test get_entries filters team entries by workspace."""
        # Create team entries in workspace
        income_entry = IncomeEntryFactory(
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )
        disbursement_entry = DisbursementEntryFactory(
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )
        
        # Create entries for different workspace
        other_workspace = WorkspaceFactory()
        IncomeEntryFactory(
            workspace=other_workspace,
            organization=other_workspace.organization,
            currency=self.usd_currency,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME, EntryType.DISBURSEMENT],
            workspace=self.workspace,
        )

        assert entries.count() == 2
        entry_ids = [entry.entry_id for entry in entries]
        assert income_entry.entry_id in entry_ids
        assert disbursement_entry.entry_id in entry_ids

    def test_get_entries_with_team_entry_types_and_organization(self):
        """Test get_entries filters team entries by organization."""
        # Create team entries in organization
        income_entry = IncomeEntryFactory(
            organization=self.organization,
            currency=self.usd_currency,
        )
        disbursement_entry = DisbursementEntryFactory(
            organization=self.organization,
            currency=self.usd_currency,
        )
        
        # Create entries for different organization
        other_org = OrganizationWithOwnerFactory()
        IncomeEntryFactory(
            organization=other_org,
            currency=self.usd_currency,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME, EntryType.DISBURSEMENT],
            organization=self.organization,
        )

        assert entries.count() == 2
        entry_ids = [entry.entry_id for entry in entries]
        assert income_entry.entry_id in entry_ids
        assert disbursement_entry.entry_id in entry_ids



    def test_get_entries_with_status_filter(self):
        """Test get_entries filters by status."""
        # Create entries with different statuses
        pending_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            status=EntryStatus.PENDING,
        )
        approved_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            status=EntryStatus.APPROVED,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME],
            workspace_team=self.workspace_team,
            statuses=[EntryStatus.PENDING],
        )

        assert entries.count() == 1
        assert entries.first().entry_id == pending_entry.entry_id

    def test_get_entries_with_type_filter(self):
        """Test get_entries filters by specific entry type."""
        # Create entries with different types
        income_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )
        disbursement_entry = DisbursementEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME, EntryType.DISBURSEMENT],
            workspace_team=self.workspace_team,
            type_filter=EntryType.INCOME,
        )

        assert entries.count() == 1
        assert entries.first().entry_id == income_entry.entry_id

    def test_get_entries_with_workspace_team_id_filter(self):
        """Test get_entries filters by workspace team ID."""
        # Create entries for different workspace teams
        income_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )
        other_workspace_team = WorkspaceTeamFactory()
        IncomeEntryFactory(
            workspace_team=other_workspace_team,
            workspace=other_workspace_team.workspace,
            organization=other_workspace_team.workspace.organization,
            currency=self.usd_currency,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME],
            workspace_team_id=str(self.workspace_team.workspace_team_id),
        )

        assert entries.count() == 1
        assert entries.first().entry_id == income_entry.entry_id

    def test_get_entries_with_workspace_id_filter(self):
        """Test get_entries filters by workspace ID."""
        # Create entries for different workspaces
        income_entry = IncomeEntryFactory(
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )
        other_workspace = WorkspaceFactory()
        IncomeEntryFactory(
            workspace=other_workspace,
            organization=other_workspace.organization,
            currency=self.usd_currency,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME],
            workspace_id=str(self.workspace.workspace_id),
        )

        assert entries.count() == 1
        assert entries.first().entry_id == income_entry.entry_id

    def test_get_entries_with_search_filter(self):
        """Test get_entries filters by search term in description."""
        # Create entries with different descriptions
        matching_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            description="Special donation for campaign",
        )
        non_matching_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            description="Regular monthly contribution",
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME],
            workspace_team=self.workspace_team,
            search="campaign",
        )

        assert entries.count() == 1
        assert entries.first().entry_id == matching_entry.entry_id

    def test_get_entries_with_prefetch_attachments(self):
        """Test get_entries prefetches attachments when requested."""
        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME],
            workspace_team=self.workspace_team,
            prefetch_attachments=True,
        )

        # Check that attachments are prefetched
        assert hasattr(entries.first(), '_prefetched_objects_cache')

    def test_get_entries_with_annotate_attachment_count(self):
        """Test get_entries annotates attachment count when requested."""
        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME],
            workspace_team=self.workspace_team,
            annotate_attachment_count=True,
        )

        # Check that attachment_count is annotated
        first_entry = entries.first()
        assert hasattr(first_entry, 'attachment_count')
        assert first_entry.attachment_count == 0  # No attachments created

    def test_get_entries_returns_none_when_no_filters(self):
        """Test get_entries returns empty queryset when no valid filters."""
        entries = get_entries(
            entry_types=[EntryType.INCOME],
            # No workspace, organization, or workspace_team specified
        )

        assert entries.count() == 0

    def test_get_entries_ordering(self):
        """Test get_entries returns entries ordered by occurred_at descending."""
        # Create entries with different dates
        from datetime import date, timedelta
        
        old_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            occurred_at=date.today() - timedelta(days=2),
        )
        recent_entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            occurred_at=date.today(),
        )

        entries = get_entries(
            entry_types=[EntryType.INCOME],
            workspace_team=self.workspace_team,
        )

        # Should be ordered by occurred_at descending (most recent first)
        assert entries.first().entry_id == recent_entry.entry_id
        assert entries.last().entry_id == old_entry.entry_id


@pytest.mark.unit
@pytest.mark.django_db
class TestGetTotalAmountOfEntries:
    """Test the get_total_amount_of_entries selector function."""

    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team_member = TeamMemberFactory()
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team_member.team
        )
        self.usd_currency = Currency.objects.get_or_create(code="USD", name="US Dollar")[0]

    def test_get_total_amount_of_entries_with_workspace_team(self):
        """Test get_total_amount_of_entries calculates total for workspace team."""
        # Create entries with different amounts and exchange rates
        IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("1.00"),
            status=EntryStatus.APPROVED,
        )
        IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("200.00"),
            exchange_rate_used=Decimal("1.50"),
            status=EntryStatus.APPROVED,
        )

        total = get_total_amount_of_entries(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            workspace_team=self.workspace_team,
        )

        # Expected: (100 * 1.00) + (200 * 1.50) = 100 + 300 = 400
        assert total == Decimal("400.00")

    def test_get_total_amount_of_entries_with_workspace(self):
        """Test get_total_amount_of_entries calculates total for workspace."""
        # Create entries with different amounts and exchange rates
        IncomeEntryFactory(
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("1.00"),
            status=EntryStatus.APPROVED,
        )
        IncomeEntryFactory(
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("200.00"),
            exchange_rate_used=Decimal("1.50"),
            status=EntryStatus.APPROVED,
        )

        total = get_total_amount_of_entries(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            workspace=self.workspace,
        )

        # Expected: (100 * 1.00) + (200 * 1.50) = 100 + 300 = 400
        assert total == Decimal("400.00")

    def test_get_total_amount_of_entries_with_organization(self):
        """Test get_total_amount_of_entries calculates total for organization."""
        # Create entries with different amounts and exchange rates
        IncomeEntryFactory(
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("1.00"),
            status=EntryStatus.APPROVED,
        )
        IncomeEntryFactory(
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("200.00"),
            exchange_rate_used=Decimal("1.50"),
            status=EntryStatus.APPROVED,
        )

        total = get_total_amount_of_entries(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            org=self.organization,
        )

        # Expected: (100 * 1.00) + (200 * 1.50) = 100 + 300 = 400
        assert total == Decimal("400.00")

    def test_get_total_amount_of_entries_filters_by_type_and_status(self):
        """Test get_total_amount_of_entries only includes matching type and status."""
        # Create approved income entries
        IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("1.00"),
            status=EntryStatus.APPROVED,
        )
        
        # Create pending income entry (should not be included)
        IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("200.00"),
            exchange_rate_used=Decimal("1.00"),
            status=EntryStatus.PENDING,
        )
        
        # Create approved disbursement entry (should not be included)
        DisbursementEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("300.00"),
            exchange_rate_used=Decimal("1.00"),
            status=EntryStatus.APPROVED,
        )

        total = get_total_amount_of_entries(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            workspace_team=self.workspace_team,
        )

        # Only the approved income entry should be included: 100 * 1.00 = 100
        assert total == Decimal("100.00")

    def test_get_total_amount_of_entries_returns_zero_when_no_matches(self):
        """Test get_total_amount_of_entries returns 0.00 when no matching entries."""
        total = get_total_amount_of_entries(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            workspace_team=self.workspace_team,
        )

        assert total == Decimal("0.00")

    def test_get_total_amount_of_entries_with_decimal_precision(self):
        """Test get_total_amount_of_entries handles decimal precision correctly."""
        # Create entries with precise decimal amounts
        IncomeEntryFactory(
            workspace_team=self.workspace_team,
            workspace=self.workspace,
            organization=self.organization,
            currency=self.usd_currency,
            amount=Decimal("33.33"),
            exchange_rate_used=Decimal("1.234567"),
            status=EntryStatus.APPROVED,
        )

        total = get_total_amount_of_entries(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            workspace_team=self.workspace_team,
        )

        # Expected: 33.33 * 1.234567 = 41.14799811, rounded to 2 decimal places
        expected = Decimal("33.33") * Decimal("1.234567")
        assert total == expected


@pytest.mark.unit
@pytest.mark.django_db
class TestGetEntry:
    """Test the get_entry selector function."""

    def setup_method(self):
        """Set up test data."""
        self.entry = EntryFactory()

    def test_get_entry_returns_entry(self):
        """Test get_entry returns the correct entry."""
        retrieved_entry = get_entry(self.entry.entry_id)
        assert retrieved_entry.entry_id == self.entry.entry_id

    def test_get_entry_with_required_attachment_count(self):
        """Test get_entry annotates attachment count when requested."""
        retrieved_entry = get_entry(
            self.entry.entry_id, 
            required_attachment_count=True
        )
        
        assert hasattr(retrieved_entry, 'attachment_count')
        assert retrieved_entry.attachment_count == 0  # No attachments created

    def test_get_entry_returns_404_for_nonexistent_entry(self):
        """Test get_entry returns 404 for non-existent entry."""
        import uuid
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(Exception):  # get_object_or_404 raises Http404
            get_entry(non_existent_id)

    def test_get_entry_without_attachment_count(self):
        """Test get_entry doesn't annotate attachment count by default."""
        retrieved_entry = get_entry(self.entry.entry_id)
        
        assert not hasattr(retrieved_entry, 'attachment_count')
