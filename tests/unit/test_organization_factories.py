"""
Unit tests for Organization factories.
"""

import pytest
from decimal import Decimal
from datetime import date

from apps.organizations.models import Organization, OrganizationMember, OrganizationExchangeRate
from apps.organizations.constants import StatusChoices
from apps.currencies.models import Currency
from tests.factories import (
    OrganizationFactory,
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
    InactiveOrganizationMemberFactory,
    ArchivedOrganizationFactory,
    OrganizationExchangeRateFactory,
    CustomUserFactory,
)


@pytest.mark.django_db
class TestOrganizationFactories:
    """Test organization-related factories."""

    def test_organization_factory_creates_valid_organization(self):
        """Test OrganizationFactory creates a valid organization."""
        org = OrganizationFactory()

        assert isinstance(org, Organization)
        assert org.organization_id is not None
        assert org.title.startswith("Organization")
        assert org.description is not None
        assert org.status == StatusChoices.ACTIVE
        assert org.owner is None

    def test_organization_factory_creates_unique_titles(self):
        """Test OrganizationFactory creates organizations with unique titles."""
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()

        assert org1.title != org2.title
        assert org1.title.startswith("Organization")
        assert org2.title.startswith("Organization")

    def test_organization_factory_creates_with_custom_values(self):
        """Test OrganizationFactory accepts custom values."""
        custom_title = "Custom Org Title"
        custom_description = "Custom description"
        custom_status = StatusChoices.CLOSED

        org = OrganizationFactory(
            title=custom_title,
            description=custom_description,
            status=custom_status
        )

        assert org.title == custom_title
        assert org.description == custom_description
        assert org.status == custom_status


@pytest.mark.django_db
class TestOrganizationWithOwnerFactory:
    """Test OrganizationWithOwnerFactory."""

    def test_organization_with_owner_factory_creates_organization_with_owner(self):
        """Test OrganizationWithOwnerFactory creates organization with owner."""
        org = OrganizationWithOwnerFactory()

        assert isinstance(org, Organization)
        assert org.owner is not None
        assert isinstance(org.owner, OrganizationMember)
        assert org.owner.organization == org

    def test_organization_with_owner_factory_uses_existing_user(self):
        """Test OrganizationWithOwnerFactory can use existing user."""
        user = CustomUserFactory()
        org = OrganizationWithOwnerFactory(owner=user)

        assert org.owner.user == user
        assert org.owner.organization == org

    def test_organization_with_owner_factory_creates_new_user_if_none_provided(self):
        """Test OrganizationWithOwnerFactory creates new user if none provided."""
        org = OrganizationWithOwnerFactory()

        assert org.owner is not None
        assert org.owner.user is not None
        assert org.owner.organization == org


@pytest.mark.django_db
class TestOrganizationMemberFactories:
    """Test organization member factories."""

    def test_organization_member_factory_creates_valid_member(self):
        """Test OrganizationMemberFactory creates a valid member."""
        member = OrganizationMemberFactory()

        assert isinstance(member, OrganizationMember)
        assert member.organization_member_id is not None
        assert member.organization is not None
        assert member.user is not None
        assert member.is_active is True

    def test_organization_member_factory_creates_with_custom_values(self):
        """Test OrganizationMemberFactory accepts custom values."""
        org = OrganizationFactory()
        user = CustomUserFactory()
        is_active = False

        member = OrganizationMemberFactory(
            organization=org,
            user=user,
            is_active=is_active
        )

        assert member.organization == org
        assert member.user == user
        assert member.is_active == is_active

    def test_inactive_organization_member_factory_creates_inactive_member(self):
        """Test InactiveOrganizationMemberFactory creates inactive member."""
        member = InactiveOrganizationMemberFactory()

        assert isinstance(member, OrganizationMember)
        assert member.is_active is False

    def test_inactive_organization_member_factory_inherits_from_base(self):
        """Test InactiveOrganizationMemberFactory inherits from base factory."""
        member = InactiveOrganizationMemberFactory()

        assert member.organization is not None
        assert member.user is not None
        assert member.organization_member_id is not None


@pytest.mark.django_db
class TestArchivedOrganizationFactory:
    """Test ArchivedOrganizationFactory."""

    def test_archived_organization_factory_creates_archived_organization(self):
        """Test ArchivedOrganizationFactory creates archived organization."""
        org = ArchivedOrganizationFactory()

        assert isinstance(org, Organization)
        assert org.status == StatusChoices.ARCHIVED
        assert org.title.startswith("Archived Organization")

    def test_archived_organization_factory_inherits_from_base(self):
        """Test ArchivedOrganizationFactory inherits from base factory."""
        org = ArchivedOrganizationFactory()

        assert org.organization_id is not None
        assert org.description is not None
        assert org.owner is None


@pytest.mark.django_db
class TestOrganizationExchangeRateFactory:
    """Test OrganizationExchangeRateFactory."""

    def test_organization_exchange_rate_factory_creates_valid_exchange_rate(self):
        """Test OrganizationExchangeRateFactory creates valid exchange rate."""
        exchange_rate = OrganizationExchangeRateFactory()

        assert isinstance(exchange_rate, OrganizationExchangeRate)
        assert exchange_rate.organization_exchange_rate_id is not None
        assert exchange_rate.organization is not None
        assert exchange_rate.currency is not None
        assert exchange_rate.rate == Decimal("1.25")
        assert exchange_rate.effective_date == date.today()
        assert exchange_rate.note is not None
        assert exchange_rate.added_by is not None

    def test_organization_exchange_rate_factory_creates_with_custom_values(self):
        """Test OrganizationExchangeRateFactory accepts custom values."""
        org = OrganizationFactory()
        currency = Currency.objects.create(code="EUR", name="Euro")
        custom_rate = Decimal("0.85")
        custom_date = date(2024, 1, 1)
        custom_note = "Custom note"
        added_by = OrganizationMemberFactory()

        exchange_rate = OrganizationExchangeRateFactory(
            organization=org,
            currency=currency,
            rate=custom_rate,
            effective_date=custom_date,
            note=custom_note,
            added_by=added_by
        )

        assert exchange_rate.organization == org
        assert exchange_rate.currency == currency
        assert exchange_rate.rate == custom_rate
        assert exchange_rate.effective_date == custom_date
        assert exchange_rate.note == custom_note
        assert exchange_rate.added_by == added_by

    def test_organization_exchange_rate_factory_creates_usd_currency(self):
        """Test OrganizationExchangeRateFactory creates USD currency if none exists."""
        # Ensure no USD currency exists
        Currency.objects.filter(code="USD").delete()
        
        exchange_rate = OrganizationExchangeRateFactory()
        
        assert exchange_rate.currency.code == "USD"
        assert exchange_rate.currency.name == "US Dollar"

    def test_organization_exchange_rate_factory_uses_existing_usd_currency(self):
        """Test OrganizationExchangeRateFactory uses existing USD currency."""
        # Create USD currency first
        usd_currency = Currency.objects.create(code="USD", name="US Dollar")
        
        exchange_rate = OrganizationExchangeRateFactory()
        
        assert exchange_rate.currency == usd_currency


@pytest.mark.django_db
class TestOrganizationFactoryRelationships:
    """Test relationships between organization factories."""

    def test_organization_member_belongs_to_organization(self):
        """Test that organization member belongs to correct organization."""
        org = OrganizationFactory()
        member = OrganizationMemberFactory(organization=org)

        assert member.organization == org
        assert member in org.members.all()

    def test_organization_exchange_rate_belongs_to_organization(self):
        """Test that organization exchange rate belongs to correct organization."""
        org = OrganizationFactory()
        exchange_rate = OrganizationExchangeRateFactory(organization=org)

        assert exchange_rate.organization == org
        assert exchange_rate in org.organization_exchange_rates.all()

    def test_organization_with_owner_creates_member_relationship(self):
        """Test that organization with owner creates proper member relationship."""
        org = OrganizationWithOwnerFactory()

        assert org.owner is not None
        assert org.owner.organization == org
        assert org.owner in org.members.all()
        assert org.owner.user is not None
