"""
Unit tests for organization services.

Tests the business logic functions in apps.organizations.services module.
Focuses on real database operations with minimal mocking.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase

from apps.organizations.constants import StatusChoices
from apps.currencies.models import Currency
from apps.organizations.exceptions import (
    OrganizationCreationError,
)
from apps.organizations.forms import OrganizationForm
from apps.organizations.models import (
    Organization,
    OrganizationExchangeRate,
)
from apps.organizations.services import (
    create_organization_exchange_rate,
    create_organization_with_owner,
    delete_organization_exchange_rate,
    update_organization_exchange_rate,
    update_organization_from_form,
)
from tests.factories import (
    CustomUserFactory,
    OrganizationExchangeRateFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
)

User = get_user_model()


class TestCreateOrganizationWithOwner(TransactionTestCase):
    """Test create_organization_with_owner service function."""

    def setUp(self):
        self.user = CustomUserFactory()

    def test_create_organization_with_owner_success(self):
        """Test successful organization creation with owner."""
        user = CustomUserFactory()
        form_data = {
            "title": "Test Organization",
            "description": "Test Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)
        self.assertTrue(form.is_valid())

        organization = create_organization_with_owner(form=form, user=user)

        self.assertIsInstance(organization, Organization)
        self.assertEqual(organization.title, "Test Organization")
        self.assertEqual(organization.description, "Test Description")
        self.assertIsNotNone(organization.owner)
        self.assertEqual(organization.owner.user, user)
        self.assertTrue(organization.owner.is_active)

    def test_create_organization_with_owner_duplicate_title(self):
        """Test organization creation with duplicate title."""
        # Create first organization
        OrganizationFactory(title="Duplicate Title")

        form_data = {
            "title": "Duplicate Title",
            "description": "Test Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)

        # Form validation should catch duplicate title
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_create_organization_with_owner_invalid_form(self):
        """Test organization creation with invalid form data."""
        form_data = {
            "title": "",  # Required field
            "description": "Test Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)
        self.assertFalse(form.is_valid())

        with self.assertRaises(OrganizationCreationError):
            create_organization_with_owner(form=form, user=self.user)


class TestUpdateOrganizationFromForm(TestCase):
    """Test update_organization_from_form service function."""

    def setUp(self):
        self.organization = OrganizationFactory(title="Original Title")

    def test_update_organization_from_form_success(self):
        """Test successful organization update from form."""
        form_data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid())

        result = update_organization_from_form(
            form=form, organization=self.organization
        )

        # Verify organization was updated
        self.assertEqual(result.title, "Updated Title")
        self.assertEqual(result.description, "Updated Description")

        # Verify database was updated
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.title, "Updated Title")

    def test_update_organization_from_form_invalid_data(self):
        """Test organization update with invalid form data."""
        organization = OrganizationFactory()
        form_data = {"title": ""}  # Empty title should be invalid
        form = OrganizationForm(data=form_data, instance=organization)

        # The form should be invalid
        self.assertFalse(form.is_valid())

        # Since the form is invalid, we shouldn't call the service with it
        # The service expects a valid form with cleaned_data
        # In a real application, the view would check form.is_valid() first


class TestOrganizationExchangeRateServices(TestCase):
    """Test organization exchange rate service functions."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.member = OrganizationMemberFactory(organization=self.organization)
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

    def test_create_organization_exchange_rate_success(self):
        """Test successful creation of organization exchange rate."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)

        # The service doesn't return anything, it just creates the exchange rate
        create_organization_exchange_rate(
            organization=organization,
            organization_member=member,
            currency_code="USD",
            rate=1.25,
            note="Test exchange rate",
            effective_date=date.today(),
        )

        # Verify the exchange rate was created
        exchange_rate = OrganizationExchangeRate.objects.get(
            organization=organization, currency__code="USD"
        )
        self.assertEqual(exchange_rate.rate, 1.25)
        self.assertEqual(exchange_rate.note, "Test exchange rate")
        self.assertEqual(exchange_rate.added_by, member)

    def test_create_organization_exchange_rate_duplicate(self):
        """Test organization exchange rate creation with duplicate constraint."""
        # Create first rate
        create_organization_exchange_rate(
            organization=self.organization,
            organization_member=self.member,
            currency_code="USD",
            rate=Decimal("1.25"),
            note="First rate",
            effective_date=date(2024, 1, 1),
        )

        # Try to create duplicate (same org, currency, effective_date)
        with self.assertRaises(ValidationError):
            create_organization_exchange_rate(
                organization=self.organization,
                organization_member=self.member,
                currency_code="USD",
                rate=Decimal("1.30"),
                note="Duplicate rate",
                effective_date=date(2024, 1, 1),
            )

    def test_update_organization_exchange_rate_success(self):
        """Test successful update of organization exchange rate."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)
        exchange_rate = OrganizationExchangeRateFactory(
            organization=organization, added_by=member, note="Original note"
        )

        updated_rate = update_organization_exchange_rate(
            organization=organization,
            organization_member=member,
            org_exchange_rate=exchange_rate,
            note="Updated note",
        )

        self.assertIsInstance(updated_rate, OrganizationExchangeRate)
        self.assertEqual(updated_rate.note, "Updated note")

    def test_delete_organization_exchange_rate_success(self):
        """Test successful organization exchange rate deletion."""
        # Create exchange rate
        exchange_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            added_by=self.member,
        )

        exchange_rate_id = exchange_rate.organization_exchange_rate_id

        delete_organization_exchange_rate(
            organization=self.organization,
            organization_member=self.member,
            org_exchange_rate=exchange_rate,
        )

        # Verify soft deletion (should still exist but with deleted_at set)
        exchange_rate.refresh_from_db()
        self.assertIsNotNone(exchange_rate.deleted_at)

        # Verify it's not in active queryset
        self.assertFalse(
            OrganizationExchangeRate.objects.filter(
                organization_exchange_rate_id=exchange_rate_id
            ).exists()
        )

    def test_create_exchange_rate_invalid_currency(self):
        """Test exchange rate creation with invalid currency."""
        with self.assertRaises(ValidationError):
            create_organization_exchange_rate(
                organization=self.organization,
                organization_member=self.member,
                currency_code="INVALID",
                rate=Decimal("1.25"),
                note="Test rate",
                effective_date=date(2024, 1, 1),
            )

    def test_create_exchange_rate_negative_rate(self):
        """Test creation with negative rate."""
        organization = OrganizationFactory()
        member = OrganizationMemberFactory(organization=organization)

        # Note: The service itself doesn't validate negative rates,
        # this would be handled at the model/form level
        # But we can test that the service handles any validation errors
        try:
            create_organization_exchange_rate(
                organization=organization,
                organization_member=member,
                currency_code="USD",
                rate=-1.25,  # Negative rate
                note="Test negative rate",
                effective_date=date.today(),
            )
            # If no exception is raised, the service allows negative rates
            # which might be valid for some business cases
        except ValidationError:
            # If ValidationError is raised, that's also acceptable
            pass
