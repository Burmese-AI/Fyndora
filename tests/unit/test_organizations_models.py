"""
Unit tests for Organization, OrganizationMember, and OrganizationExchangeRate models.

Tests cover:
- Organization model creation with defaults, expense validation, status choices, string representation
- OrganizationMember model creation, unique constraints, string representation, is_org_owner property
- OrganizationExchangeRate model creation, unique constraints, soft delete behavior, cascade delete
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.currencies.models import Currency
from apps.organizations.constants import StatusChoices
from apps.organizations.models import (
    Organization,
    OrganizationExchangeRate,
    OrganizationMember,
)
from tests.factories import (
    CustomUserFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
)


@pytest.mark.unit
class TestOrganizationModel(TestCase):
    """Test the Organization model - essential functionality only."""

    @pytest.mark.django_db
    def test_organization_creation_with_defaults(self):
        """Test creating organization with default values."""
        org = OrganizationFactory()

        # Check defaults
        self.assertEqual(org.status, StatusChoices.ACTIVE)
        self.assertEqual(org.expense, Decimal("0.00"))
        self.assertIsNotNone(org.organization_id)  # UUID generated
        self.assertIsNone(org.owner)  # No owner initially

    @pytest.mark.django_db
    def test_organization_expense_validation_non_negative(self):
        """Test that expense field validates non-negative values."""
        # Valid case: zero expense
        org = Organization(title="Test Org", expense=Decimal("0.00"))
        org.full_clean()  # Should not raise

        # Valid case: positive expense
        org.expense = Decimal("100.50")
        org.full_clean()  # Should not raise

        # Invalid case: negative expense
        org.expense = Decimal("-10.00")
        with self.assertRaises(ValidationError):
            org.full_clean()

    def test_organization_status_choices_validation(self):
        """Test that status field validates against available choices."""
        org = Organization(title="Test Org")

        # Valid statuses
        for status, _ in StatusChoices.choices:
            org.status = status
            org.full_clean()  # Should not raise

        # Invalid status would be caught by Django field validation
        # No need to test Django's internal choice validation

    def test_organization_str_representation(self):
        """Test string representation returns title."""
        org = OrganizationFactory.build(title="My Organization")
        self.assertEqual(str(org), "My Organization")

    @pytest.mark.django_db
    def test_organization_title_uniqueness_per_owner(self):
        """Test that organization titles must be unique per owner."""
        # Create an organization with an owner
        member = OrganizationMemberFactory()
        org1 = OrganizationFactory(title="Unique Organization")
        org1.owner = member
        org1.save()

        # Try to create another organization with same title and same owner - should fail
        with self.assertRaises(IntegrityError):
            org2 = Organization.objects.create(
                title="Unique Organization", owner=member
            )

    @pytest.mark.django_db
    def test_organization_title_different_owners_allowed(self):
        """Test that same title is allowed for different owners."""
        # Create two different owners
        member1 = OrganizationMemberFactory()
        member2 = OrganizationMemberFactory()

        # Create organizations with same title but different owners - should work
        org1 = OrganizationFactory(title="Same Title")
        org1.owner = member1
        org1.save()

        org2 = OrganizationFactory(title="Same Title")
        org2.owner = member2
        org2.save()

        # Both should exist
        self.assertEqual(Organization.objects.filter(title="Same Title").count(), 2)


@pytest.mark.unit
class TestOrganizationMemberModel(TestCase):
    """Test the OrganizationMember model - essential functionality only."""

    def test_organization_member_str_representation(self):
        """Test string representation format."""
        user = CustomUserFactory.build(username="testuser")
        organization = OrganizationFactory.build(title="Test Org")
        member = OrganizationMember(organization=organization, user=user)

        expected = "testuser in Test Org"
        self.assertEqual(str(member), expected)

    @pytest.mark.django_db
    def test_organization_member_unique_constraint(self):
        """Test unique constraint on organization + user."""
        user = CustomUserFactory()
        organization = OrganizationFactory()

        # Create first member
        OrganizationMemberFactory(organization=organization, user=user)

        # Try to create duplicate - should fail
        with self.assertRaises(IntegrityError):
            OrganizationMemberFactory(organization=organization, user=user)

    @pytest.mark.django_db
    def test_organization_member_is_org_owner_property_true(self):
        """Test is_org_owner property returns True when member is owner."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)

        # Set member as owner
        organization.owner = member
        organization.save()

        self.assertTrue(member.is_org_owner)

    @pytest.mark.django_db
    def test_organization_member_is_org_owner_property_false(self):
        """Test is_org_owner property returns False when member is not owner."""
        organization = OrganizationFactory()
        member1 = OrganizationMemberFactory(organization=organization)
        member2 = OrganizationMemberFactory(organization=organization)

        # Set member1 as owner
        organization.owner = member1
        organization.save()

        # member2 should not be owner
        self.assertFalse(member2.is_org_owner)

    @pytest.mark.django_db
    def test_organization_member_is_org_owner_property_no_owner(self):
        """Test is_org_owner property returns False when organization has no owner."""
        member = OrganizationMemberFactory()

        # Organization has no owner by default
        self.assertIsNone(member.organization.owner)
        self.assertFalse(member.is_org_owner)


@pytest.mark.unit
class TestOrganizationExchangeRateModel(TestCase):
    """Test the OrganizationExchangeRate model - essential functionality only."""

    @pytest.mark.django_db
    def test_organization_exchange_rate_creation_with_defaults(self):
        """Test creating organization exchange rate with required fields."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)
        currency = Currency.objects.create(code="USD", name="US Dollar")

        exchange_rate = OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=Decimal("1.25"),
            effective_date=date(2024, 1, 1),
            added_by=member,
        )

        # Check required fields
        self.assertEqual(exchange_rate.organization, organization)
        self.assertEqual(exchange_rate.currency, currency)
        self.assertEqual(exchange_rate.rate, Decimal("1.25"))
        self.assertEqual(exchange_rate.effective_date, date(2024, 1, 1))
        self.assertEqual(exchange_rate.added_by, member)
        self.assertIsNotNone(
            exchange_rate.organization_exchange_rate_id
        )  # UUID generated
        self.assertIsNone(exchange_rate.deleted_at)  # SoftDeleteModel default

    @pytest.mark.django_db
    def test_organization_exchange_rate_unique_constraint(self):
        """Test unique constraint on organization + currency + effective_date."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)
        currency = Currency.objects.create(code="USD", name="US Dollar")
        effective_date = date(2024, 1, 1)

        # Create first exchange rate
        OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=Decimal("1.25"),
            effective_date=effective_date,
            added_by=member,
        )

        # Try to create duplicate - should fail
        with self.assertRaises(IntegrityError):
            OrganizationExchangeRate.objects.create(
                organization=organization,
                currency=currency,
                rate=Decimal("1.30"),
                effective_date=effective_date,
                added_by=member,
            )

    @pytest.mark.django_db
    def test_organization_exchange_rate_different_organizations_allowed(self):
        """Test that same currency and date allowed for different organizations."""
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        member1 = OrganizationMemberFactory(organization=org1)
        member2 = OrganizationMemberFactory(organization=org2)
        currency = Currency.objects.create(code="USD", name="US Dollar")
        effective_date = date(2024, 1, 1)

        # Create exchange rate for org1
        rate1 = OrganizationExchangeRate.objects.create(
            organization=org1,
            currency=currency,
            rate=Decimal("1.25"),
            effective_date=effective_date,
            added_by=member1,
        )

        # Create exchange rate for org2 with same currency and date - should work
        rate2 = OrganizationExchangeRate.objects.create(
            organization=org2,
            currency=currency,
            rate=Decimal("1.30"),
            effective_date=effective_date,
            added_by=member2,
        )

        self.assertNotEqual(rate1.organization, rate2.organization)
        self.assertEqual(rate1.currency, rate2.currency)
        self.assertEqual(rate1.effective_date, rate2.effective_date)

    @pytest.mark.django_db
    def test_organization_exchange_rate_different_dates_allowed(self):
        """Test that same organization and currency allowed for different dates."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)
        currency = Currency.objects.create(code="USD", name="US Dollar")

        # Create exchange rate for Jan 1
        rate1 = OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=Decimal("1.25"),
            effective_date=date(2024, 1, 1),
            added_by=member,
        )

        # Create exchange rate for Jan 2 - should work
        rate2 = OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=Decimal("1.30"),
            effective_date=date(2024, 1, 2),
            added_by=member,
        )

        self.assertEqual(rate1.organization, rate2.organization)
        self.assertEqual(rate1.currency, rate2.currency)
        self.assertNotEqual(rate1.effective_date, rate2.effective_date)

    @pytest.mark.django_db
    def test_organization_exchange_rate_soft_delete_allows_duplicate(self):
        """Test that soft deleted exchange rate allows creating new one with same constraints."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)
        currency = Currency.objects.create(code="USD", name="US Dollar")
        effective_date = date(2024, 1, 1)

        # Create and soft delete first exchange rate
        rate1 = OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=Decimal("1.25"),
            effective_date=effective_date,
            added_by=member,
        )
        rate1.delete()  # Soft delete

        # Create new exchange rate with same constraints - should work
        rate2 = OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=Decimal("1.30"),
            effective_date=effective_date,
            added_by=member,
        )

        self.assertIsNotNone(rate1.deleted_at)
        self.assertIsNone(rate2.deleted_at)

    @pytest.mark.django_db
    def test_organization_exchange_rate_cascade_delete_organization(self):
        """Test that exchange rates are deleted when organization is deleted."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)
        currency = Currency.objects.create(code="USD", name="US Dollar")

        exchange_rate = OrganizationExchangeRate.objects.create(
            organization=organization,
            currency=currency,
            rate=Decimal("1.25"),
            effective_date=date(2024, 1, 1),
            added_by=member,
        )

        exchange_rate_id = exchange_rate.organization_exchange_rate_id

        # Delete organization
        organization.delete()

        # Exchange rate should be deleted
        self.assertFalse(
            OrganizationExchangeRate.objects.filter(
                organization_exchange_rate_id=exchange_rate_id
            ).exists()
        )
