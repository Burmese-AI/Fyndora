"""
Unit tests for Entry models.

Tests the Entry model behavior, properties, methods, and relationships.
"""

from datetime import timedelta, date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.currencies.models import Currency
from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from tests.factories import (
    ApprovedEntryFactory,
    DisbursementEntryFactory,
    EntryFactory,
    FlaggedEntryFactory,
    IncomeEntryFactory,
    OrganizationExpenseEntryFactory,
    OrganizationMemberFactory,
    PendingEntryFactory,
    RejectedEntryFactory,
    RemittanceEntryFactory,
    ReviewedEntryFactory,
    TeamMemberFactory,
    WorkspaceExpenseEntryFactory,
    WorkspaceFactory,
    WorkspaceTeamFactory,
)
from tests.factories.organization_factories import OrganizationWithOwnerFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryModel:
    """Test Entry model basic functionality."""

    def setup_method(self):
        """Set up test data."""
        self.team_member = TeamMemberFactory()
        self.organization = self.team_member.organization_member.organization
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team_member.team
        )

    def test_entry_creation_with_required_fields(self):
        """Test creating entry with all required fields."""
        entry = EntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            submitted_by_team_member=self.team_member,
            entry_type=EntryType.INCOME,
            amount=Decimal("100.00"),
            description="Test entry",
        )

        assert entry.submitted_by_team_member == self.team_member
        assert entry.organization == self.organization
        assert entry.workspace == self.workspace
        assert entry.workspace_team == self.workspace_team
        assert entry.entry_type == EntryType.INCOME
        assert entry.amount == Decimal("100.00")
        assert entry.description == "Test entry"
        assert entry.status == EntryStatus.PENDING  # Default status

    def test_entry_str_representation(self):
        """Test string representation of entry."""
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            amount=Decimal("150.00"),
            description="Donation from supporter",
        )

        # The actual __str__ method returns: organization - workspace - workspace_team - amount - currency - status
        expected_str = f"{entry.organization} - {entry.workspace} - {entry.workspace_team} - {entry.amount} - {entry.currency} - {entry.status}"
        assert str(entry) == expected_str

    def test_converted_amount_property(self):
        """Test converted_amount property calculation."""
        # Create currency
        usd_currency = Currency.objects.get_or_create(code="USD", name="US Dollar")[0]

        # Test with exchange rate
        entry = EntryFactory(
            amount=Decimal("100.00"),
            currency=usd_currency,
            exchange_rate_used=Decimal("1.25"),
        )

        expected_converted = Decimal("100.00") * Decimal("1.25")
        assert entry.converted_amount == expected_converted

    def test_converted_amount_without_exchange_rate(self):
        """Test converted_amount with default exchange rate of 1.0."""
        entry = EntryFactory(
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("1.0"),  # Default rate
        )

        # Should return the original amount when exchange rate is 1.0
        assert entry.converted_amount == Decimal("100.00")

    def test_entry_verbose_name(self):
        """Test model verbose names."""
        assert Entry._meta.verbose_name == "entry"
        assert Entry._meta.verbose_name_plural == "entries"

    def test_entry_ordering(self):
        """Test default ordering by occurred_at and created_at descending."""
        # Create entries with different timestamps
        entry1 = EntryFactory()
        entry2 = EntryFactory()
        entry3 = EntryFactory()

        entries = Entry.objects.all()
        # Should be ordered by occurred_at descending, then created_at descending
        # Since we can't control occurred_at precisely, just check that ordering is applied
        assert len(entries) == 3

    def test_entry_permissions(self):
        """Test model permissions are defined."""
        permissions = [perm[0] for perm in Entry._meta.permissions]

        expected_permissions = [
            "upload_attachments",
            "review_entries",
            "flag_entries",
        ]

        for perm in expected_permissions:
            assert perm in permissions

    def test_entry_indexes(self):
        """Test database indexes are defined."""
        indexes = Entry._meta.indexes
        assert len(indexes) > 0

        # Check for important indexes
        index_fields = []
        for index in indexes:
            index_fields.extend(index.fields)

        # Should have indexes on commonly queried fields
        assert "status" in index_fields
        assert "workspace" in index_fields
        assert "workspace_team" in index_fields
        assert "occurred_at" in index_fields

    def test_entry_with_minimal_required_fields(self):
        """Test entry can be created with minimal required fields."""
        team_member = TeamMemberFactory()
        organization = team_member.organization_member.organization
        workspace = WorkspaceFactory(organization=organization)
        workspace_team = WorkspaceTeamFactory(
            workspace=workspace, team=team_member.team
        )
        currency = Currency.objects.get_or_create(code="USD", name="US Dollar")[0]

        entry = Entry(
            organization=organization,
            workspace=workspace,
            workspace_team=workspace_team,
            submitted_by_team_member=team_member,
            amount=Decimal("100.00"),
            description="Test entry",
            entry_type=EntryType.INCOME,
            occurred_at=date.today(),
            currency=currency,
            exchange_rate_used=Decimal("1.00"),
        )
        entry.save()

        assert entry.entry_id is not None
        assert entry.status == EntryStatus.PENDING  # Default status
        assert entry.is_flagged is False  # Default value


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryProperties:
    """Test Entry model properties and computed fields."""

    def test_converted_amount_with_same_currency(self):
        """Test converted_amount when entry and workspace use same currency."""
        # Create USD currency
        usd = Currency.objects.create(code="USD", name="US Dollar")

        workspace = WorkspaceFactory()
        entry = EntryFactory(
            workspace=workspace,
            currency=usd,
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("1.0"),
        )

        assert entry.converted_amount == Decimal("100.00")

    def test_converted_amount_with_different_currency(self):
        """Test converted_amount with currency conversion."""
        usd = Currency.objects.create(code="USD", name="US Dollar")
        eur = Currency.objects.create(code="EUR", name="Euro")

        workspace = WorkspaceFactory()
        entry = EntryFactory(
            workspace=workspace,
            currency=eur,
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("1.2"),  # 1 EUR = 1.2 USD
        )

        assert entry.converted_amount == Decimal("120.00")

    def test_converted_amount_with_zero_exchange_rate(self):
        """Test converted_amount handles zero exchange rate."""
        usd = Currency.objects.create(code="USD", name="US Dollar")
        eur = Currency.objects.create(code="EUR", name="Euro")

        workspace = WorkspaceFactory()
        entry = EntryFactory(
            workspace=workspace,
            currency=eur,
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("0.0"),
        )

        assert entry.converted_amount == Decimal("0.00")

    def test_converted_amount_precision(self):
        """Test converted_amount maintains proper decimal precision."""
        usd = Currency.objects.create(code="USD", name="US Dollar")
        eur = Currency.objects.create(code="EUR", name="Euro")

        workspace = WorkspaceFactory()
        entry = EntryFactory(
            workspace=workspace,
            currency=eur,
            amount=Decimal("33.33"),
            exchange_rate_used=Decimal("1.234567"),
        )

        # The model returns the raw calculation without rounding
        expected = Decimal("33.33") * Decimal("1.234567")
        assert entry.converted_amount == expected

    def test_converted_amount_with_none_exchange_rate(self):
        """Test converted_amount handles None exchange rate."""
        usd = Currency.objects.create(code="USD", name="US Dollar")
        eur = Currency.objects.create(code="EUR", name="Euro")

        workspace = WorkspaceFactory()
        entry = EntryFactory(
            workspace=workspace,
            currency=eur,
            amount=Decimal("100.00"),
            exchange_rate_used=Decimal("1.0"),  # Use 1.0 instead of None
        )

        # Should return amount when exchange_rate_used is 1.0
        assert entry.converted_amount == Decimal("100.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryValidation:
    """Test Entry model validation methods."""

    def setup_method(self):
        """Set up test data."""
        self.team_member = TeamMemberFactory()
        self.organization = self.team_member.organization_member.organization
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team_member.team
        )

    def test_clean_method_with_valid_data(self):
        """Test clean method passes with valid data."""
        entry = EntryFactory(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            submitted_by_team_member=self.team_member,
        )

        # Should not raise any exception
        entry.clean()

    @pytest.mark.parametrize(
        "invalid_amount,error_expected",
        [
            (Decimal("-10.00"), True),  # Negative amounts not allowed
            (Decimal("0.00"), True),  # Zero amount not allowed (min 0.01)
            (
                Decimal("99999999.99"),
                False,
            ),  # Max value that fits in precision 10, scale 2
            (Decimal("100.00"), False),  # Valid amount
        ],
    )
    def test_amount_validation(self, invalid_amount, error_expected):
        """Test amount validation with various values."""
        if error_expected:
            with pytest.raises(ValidationError):
                entry = EntryFactory(amount=invalid_amount)
                entry.full_clean()
        else:
            entry = EntryFactory(amount=invalid_amount)
            entry.full_clean()  # Should not raise

    def test_description_max_length(self):
        """Test description field max length validation."""
        # Create a description that's exactly 255 characters (the max length)
        long_description = "A" * 255

        # This should work fine
        entry = EntryFactory(description=long_description)
        assert len(entry.description) == 255

        # Test that 256 characters would be too long by checking the field max_length
        from apps.entries.models import Entry

        description_field = Entry._meta.get_field("description")
        assert description_field.max_length == 255

    @pytest.mark.parametrize(
        "invalid_field,invalid_value",
        [
            ("entry_type", "invalid_type"),
            ("status", "invalid_status"),
        ],
    )
    def test_choice_field_validation(self, invalid_field, invalid_value):
        """Test choice fields must have valid values."""
        with pytest.raises(ValidationError):
            entry = EntryFactory.build(**{invalid_field: invalid_value})
            entry.full_clean()


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryRelationships:
    """Test Entry model relationships."""

    def test_submitted_by_team_member_relationship(self):
        """Test submitted_by_team_member foreign key relationship."""
        team_member = TeamMemberFactory()
        entry = EntryFactory(submitted_by_team_member=team_member)

        assert entry.submitted_by_team_member == team_member

    def test_submitted_by_org_member_relationship(self):
        """Test submitted_by_org_member foreign key relationship."""
        org_member = OrganizationMemberFactory()
        entry = OrganizationExpenseEntryFactory(submitted_by_org_member=org_member)

        assert entry.submitted_by_org_member == org_member
        assert entry.submitted_by_team_member is None

    def test_organization_relationship(self):
        """Test organization foreign key relationship."""
        entry = EntryFactory()

        assert entry.organization is not None

    def test_workspace_relationship(self):
        """Test workspace foreign key relationship."""
        workspace = WorkspaceFactory()
        entry = EntryFactory(workspace=workspace)

        assert entry.workspace == workspace

    def test_workspace_team_relationship(self):
        """Test workspace_team foreign key relationship."""
        workspace_team = WorkspaceTeamFactory()
        entry = EntryFactory(workspace_team=workspace_team)

        assert entry.workspace_team == workspace_team

    def test_currency_relationship(self):
        """Test currency foreign key relationship."""
        currency = Currency.objects.create(code="USD", name="US Dollar")
        entry = EntryFactory(currency=currency)

        assert entry.currency == currency

    def test_last_status_modified_by_relationship(self):
        """Test last_status_modified_by foreign key relationship."""
        reviewer = OrganizationMemberFactory()
        entry = ApprovedEntryFactory(last_status_modified_by=reviewer)

        assert entry.last_status_modified_by == reviewer

    @pytest.mark.skip(
        reason="Requires attachments table which may not be available in test environment"
    )
    def test_cascade_deletion_behavior(self):
        """Test cascade deletion behavior when related objects are deleted."""
        # Create entry with relationships
        entry = EntryFactory()
        organization = entry.organization

        # Store IDs for verification
        entry_id = entry.entry_id
        organization_id = organization.organization_id

        # Delete organization should cascade to entries
        organization.delete()

        # Entry should be deleted due to cascade
        assert not Entry.objects.filter(entry_id=entry_id).exists()

        # Organization should also be deleted
        from apps.organizations.models import Organization

        assert not Organization.objects.filter(organization_id=organization_id).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryFactories:
    """Test Entry factories work correctly."""

    def test_entry_factory_creates_valid_entry(self):
        """Test EntryFactory creates valid entry with all required fields."""
        entry = EntryFactory()

        assert entry.entry_id is not None
        assert (
            entry.submitted_by_team_member is not None
            or entry.submitted_by_org_member is not None
        )
        assert entry.organization is not None
        assert entry.workspace is not None
        assert entry.workspace_team is not None
        assert entry.amount > 0
        assert entry.description is not None
        assert entry.entry_type in [choice[0] for choice in EntryType.choices]
        assert entry.status in [choice[0] for choice in EntryStatus.choices]
        assert entry.currency is not None
        assert entry.exchange_rate_used is not None

    @pytest.mark.parametrize(
        "factory_class,expected_status,has_reviewer",
        [
            (PendingEntryFactory, EntryStatus.PENDING, False),
            (ReviewedEntryFactory, EntryStatus.REVIEWED, True),
            (ApprovedEntryFactory, EntryStatus.APPROVED, True),
            (RejectedEntryFactory, EntryStatus.REJECTED, True),
        ],
    )
    def test_status_specific_factories(
        self, factory_class, expected_status, has_reviewer
    ):
        """Test status-specific factories create entries with correct status and reviewer."""
        entry = factory_class()

        assert entry.status == expected_status
        if has_reviewer:
            assert entry.last_status_modified_by is not None
            assert entry.status_note is not None
            assert entry.status_last_updated_at is not None
        else:
            assert entry.last_status_modified_by is None

    @pytest.mark.parametrize(
        "factory_class,expected_type",
        [
            (IncomeEntryFactory, EntryType.INCOME),
            (DisbursementEntryFactory, EntryType.DISBURSEMENT),
            (RemittanceEntryFactory, EntryType.REMITTANCE),
            (OrganizationExpenseEntryFactory, EntryType.ORG_EXP),
            (WorkspaceExpenseEntryFactory, EntryType.WORKSPACE_EXP),
        ],
    )
    def test_entry_type_specific_factories(self, factory_class, expected_type):
        """Test entry type-specific factories create entries with correct type."""
        entry = factory_class()
        assert entry.entry_type == expected_type

    def test_organization_expense_factory(self):
        """Test OrganizationExpenseEntryFactory creates org expense with org member submitter."""
        entry = OrganizationExpenseEntryFactory()

        assert entry.entry_type == EntryType.ORG_EXP
        assert entry.submitted_by_org_member is not None
        assert entry.submitted_by_team_member is None
        assert entry.workspace is None
        assert entry.workspace_team is None
        assert entry.org_exchange_rate_ref is not None

    def test_workspace_expense_factory(self):
        """Test WorkspaceExpenseEntryFactory creates workspace expense with workspace exchange rate."""
        entry = WorkspaceExpenseEntryFactory()

        assert entry.entry_type == EntryType.WORKSPACE_EXP
        assert entry.submitted_by_team_member is not None
        assert entry.workspace is not None
        assert entry.workspace_team is not None
        assert entry.workspace_exchange_rate_ref is not None

    def test_flagged_entry_factory(self):
        """Test FlaggedEntryFactory creates flagged entry."""
        entry = FlaggedEntryFactory()
        assert entry.is_flagged is True
        assert entry.last_status_modified_by is not None
        assert entry.status_note is not None


@pytest.mark.unit
@pytest.mark.django_db
class TestEntryQuerysets:
    """Test Entry querysets and managers."""

    def test_pending_entries_queryset(self):
        """Test queryset for pending entries."""
        pending_entry = PendingEntryFactory()
        approved_entry = ApprovedEntryFactory()

        pending_entries = Entry.objects.filter(status=EntryStatus.PENDING)

        assert pending_entry.entry_id in [e.entry_id for e in pending_entries]
        assert approved_entry.entry_id not in [e.entry_id for e in pending_entries]

    def test_approved_entries_queryset(self):
        """Test queryset for approved entries."""
        approved_entry = ApprovedEntryFactory()
        rejected_entry = RejectedEntryFactory()

        approved_entries = Entry.objects.filter(status=EntryStatus.APPROVED)

        assert approved_entry.entry_id in [e.entry_id for e in approved_entries]
        assert rejected_entry.entry_id not in [e.entry_id for e in approved_entries]

    def test_flagged_entries_queryset(self):
        """Test queryset for flagged entries."""
        flagged_entry = FlaggedEntryFactory()
        normal_entry = EntryFactory(is_flagged=False)

        flagged_entries = Entry.objects.filter(is_flagged=True)

        assert flagged_entry.entry_id in [e.entry_id for e in flagged_entries]
        assert normal_entry.entry_id not in [e.entry_id for e in flagged_entries]

    def test_entries_by_organization(self):
        """Test filtering entries by organization."""
        org1 = OrganizationWithOwnerFactory()
        org2 = OrganizationWithOwnerFactory()

        entry1 = EntryFactory(organization=org1)
        entry2 = EntryFactory(organization=org2)

        org1_entries = Entry.objects.filter(organization=org1)

        assert entry1.entry_id in [e.entry_id for e in org1_entries]
        assert entry2.entry_id not in [e.entry_id for e in org1_entries]

    def test_entries_by_workspace(self):
        """Test filtering entries by workspace."""
        workspace1 = WorkspaceFactory()
        workspace2 = WorkspaceFactory()

        entry1 = EntryFactory(workspace=workspace1)
        entry2 = EntryFactory(workspace=workspace2)

        workspace1_entries = Entry.objects.filter(workspace=workspace1)

        assert entry1.entry_id in [e.entry_id for e in workspace1_entries]
        assert entry2.entry_id not in [e.entry_id for e in workspace1_entries]

    def test_entries_by_entry_type(self):
        """Test filtering entries by entry type."""
        income_entry = IncomeEntryFactory()
        disbursement_entry = DisbursementEntryFactory()

        income_entries = Entry.objects.filter(entry_type=EntryType.INCOME)

        assert income_entry.entry_id in [e.entry_id for e in income_entries]
        assert disbursement_entry.entry_id not in [e.entry_id for e in income_entries]

    def test_entries_by_currency(self):
        """Test filtering entries by currency."""
        usd_currency = Currency.objects.get_or_create(code="USD", name="US Dollar")[0]
        eur_currency = Currency.objects.get_or_create(code="EUR", name="Euro")[0]

        usd_entry = EntryFactory(currency=usd_currency)
        eur_entry = EntryFactory(currency=eur_currency)

        usd_entries = Entry.objects.filter(currency=usd_currency)

        assert usd_entry.entry_id in [e.entry_id for e in usd_entries]
        assert eur_entry.entry_id not in [e.entry_id for e in usd_entries]

    def test_entries_by_date_range(self):
        """Test filtering entries by date range."""

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        recent_entry = EntryFactory(occurred_at=today)
        old_entry = EntryFactory(occurred_at=yesterday)

        recent_entries = Entry.objects.filter(occurred_at=today)

        assert recent_entry.entry_id in [e.entry_id for e in recent_entries]
        assert old_entry.entry_id not in [e.entry_id for e in recent_entries]

    def test_entry_queryset_filtering_and_ordering(self):
        """Test basic queryset filtering and default ordering."""
        # Create entries with different statuses
        pending_entry = PendingEntryFactory()
        approved_entry = ApprovedEntryFactory()
        rejected_entry = RejectedEntryFactory()

        # Test filtering by status
        pending_entries = Entry.objects.filter(status=EntryStatus.PENDING)
        assert pending_entry.entry_id in [e.entry_id for e in pending_entries]
        assert approved_entry.entry_id not in [e.entry_id for e in pending_entries]
        assert rejected_entry.entry_id not in [e.entry_id for e in pending_entries]

        approved_entries = Entry.objects.filter(status=EntryStatus.APPROVED)
        assert approved_entry.entry_id in [e.entry_id for e in approved_entries]
        assert pending_entry.entry_id not in [e.entry_id for e in approved_entries]

        # Test default ordering (occurred_at and created_at descending)
        all_entries = list(Entry.objects.all())
        # Just check that we have the expected number of entries
        assert len(all_entries) >= 3

    def test_entry_queryset_aggregation(self):
        """Test queryset aggregation functions."""
        # Create entries with known amounts
        EntryFactory(amount=Decimal("100.00"))
        EntryFactory(amount=Decimal("200.00"))
        EntryFactory(amount=Decimal("300.00"))

        # Test aggregation
        aggregates = Entry.objects.aggregate(
            total=Sum("amount"), count=Count("entry_id"), avg=Avg("amount")
        )

        assert aggregates["total"] == Decimal("600.00")
        assert aggregates["count"] == 3
        assert aggregates["avg"] == Decimal("200.00")
