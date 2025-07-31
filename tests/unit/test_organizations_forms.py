"""Unit tests for organization forms.

Tests form validation, initialization, and widget behavior.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.forms import Select, Textarea, TextInput
from django.test import TestCase

from apps.currencies.models import Currency
from apps.organizations.constants import StatusChoices
from apps.organizations.forms import (
    OrganizationExchangeRateCreateForm,
    OrganizationExchangeRateUpdateForm,
    OrganizationForm,
)
from apps.organizations.models import Organization, OrganizationExchangeRate
from tests.factories import (
    OrganizationExchangeRateFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
)


class TestOrganizationForm(TestCase):
    """Test OrganizationForm validation and behavior."""

    def test_organization_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            "title": "Test Organization",
            "description": "Test Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["title"], "Test Organization")
        self.assertEqual(form.cleaned_data["description"], "Test Description")
        self.assertEqual(form.cleaned_data["status"], StatusChoices.ACTIVE)

    def test_organization_form_missing_title(self):
        """Test form validation with missing required title."""
        form_data = {
            "description": "Test Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("This field is required", str(form.errors["title"]))

    def test_organization_form_empty_title(self):
        """Test form validation with empty title."""
        form_data = {
            "title": "",
            "description": "Test Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_organization_form_optional_description(self):
        """Test form with optional description field."""
        form_data = {
            "title": "Test Organization",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["description"], "")

    @pytest.mark.django_db
    def test_organization_form_duplicate_title_create_mode(self):
        """Test form validation for duplicate title in create mode."""
        # Create existing organization
        existing_org = OrganizationFactory(title="Existing Organization")

        form_data = {
            "title": "Existing Organization",
            "description": "Test Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    @pytest.mark.django_db
    def test_organization_form_duplicate_title_edit_mode(self):
        """Test form validation for duplicate title in edit mode (should allow same title)."""
        # Create existing organization
        existing_org = OrganizationFactory(title="Existing Organization")

        form_data = {
            "title": "Existing Organization",
            "description": "Updated Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data, instance=existing_org)

        # Should be valid when editing the same organization
        self.assertTrue(form.is_valid())

    @pytest.mark.django_db
    def test_organization_form_duplicate_title_different_org_edit_mode(self):
        """Test form validation for duplicate title when editing different organization."""
        # Create two organizations
        org1 = OrganizationFactory(title="Organization One")
        org2 = OrganizationFactory(title="Organization Two")

        form_data = {
            "title": "Organization One",  # Try to use org1's title
            "description": "Updated Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data, instance=org2)

        # Should be invalid when trying to use another org's title
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_organization_form_invalid_status(self):
        """Test form validation with invalid status."""
        form_data = {
            "title": "Test Organization",
            "description": "Test Description",
            "status": "INVALID_STATUS",
        }
        form = OrganizationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)

    def test_organization_form_widget_classes(self):
        """Test form widget CSS classes."""
        form = OrganizationForm()

        # Check widget types and classes
        self.assertIsInstance(form.fields["title"].widget, TextInput)
        self.assertIsInstance(form.fields["description"].widget, Textarea)
        self.assertIsInstance(form.fields["status"].widget, Select)

        # Check CSS classes
        self.assertIn("form-input", form.fields["title"].widget.attrs.get("class", ""))
        self.assertIn(
            "form-textarea", form.fields["description"].widget.attrs.get("class", "")
        )
        self.assertIn(
            "form-select", form.fields["status"].widget.attrs.get("class", "")
        )

    def test_organization_form_initialization_with_instance(self):
        """Test form initialization with existing organization instance."""
        organization = OrganizationFactory(
            title="Test Org",
            description="Test Description",
            status=StatusChoices.ACTIVE,
        )

        form = OrganizationForm(instance=organization)

        # Check initial values
        self.assertEqual(form.initial["title"], "Test Org")
        self.assertEqual(form.initial["description"], "Test Description")
        self.assertEqual(form.initial["status"], StatusChoices.ACTIVE)

    def test_organization_form_save_creates_organization(self):
        """Test form save method creates organization."""
        form_data = {
            "title": "New Organization",
            "description": "New Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data)

        self.assertTrue(form.is_valid())
        organization = form.save()

        self.assertIsInstance(organization, Organization)
        self.assertEqual(organization.title, "New Organization")
        self.assertEqual(organization.description, "New Description")
        self.assertEqual(organization.status, StatusChoices.ACTIVE)

    def test_organization_form_save_updates_organization(self):
        """Test form save method updates existing organization."""
        organization = OrganizationFactory(title="Original Title")

        form_data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "status": StatusChoices.ACTIVE,
        }
        form = OrganizationForm(data=form_data, instance=organization)

        self.assertTrue(form.is_valid())
        updated_org = form.save()

        self.assertEqual(updated_org.organization_id, organization.organization_id)
        self.assertEqual(updated_org.title, "Updated Title")
        self.assertEqual(updated_org.description, "Updated Description")


class TestOrganizationExchangeRateCreateForm(TestCase):
    """Test OrganizationExchangeRateCreateForm validation and behavior."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.member = OrganizationMemberFactory(organization=self.organization)
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

    def test_exchange_rate_create_form_inheritance(self):
        """Test that create form inherits from base form."""
        from apps.currencies.forms import BaseExchangeRateCreateForm

        form = OrganizationExchangeRateCreateForm()
        self.assertIsInstance(form, BaseExchangeRateCreateForm)

    def test_exchange_rate_create_form_valid_data(self):
        """Test create form with valid data."""
        form_data = {
            "currency": self.currency.currency_id,
            "rate": "1.25",
            "effective_date": "2024-01-01",
            "note": "Test exchange rate",
        }
        form = OrganizationExchangeRateCreateForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["currency"], self.currency)
        self.assertEqual(form.cleaned_data["rate"], Decimal("1.25"))
        self.assertEqual(form.cleaned_data["effective_date"], date(2024, 1, 1))
        self.assertEqual(form.cleaned_data["note"], "Test exchange rate")

    def test_exchange_rate_create_form_missing_required_fields(self):
        """Test create form with missing required fields."""
        form_data = {
            "note": "Test exchange rate",
        }
        form = OrganizationExchangeRateCreateForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("currency", form.errors)
        self.assertIn("rate", form.errors)
        self.assertIn("effective_date", form.errors)

    def test_exchange_rate_create_form_invalid_rate(self):
        """Test create form with invalid rate values."""
        # Test negative rate
        form_data = {
            "currency": self.currency.currency_id,
            "rate": "-1.25",
            "effective_date": "2024-01-01",
            "note": "Test exchange rate",
        }
        form = OrganizationExchangeRateCreateForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("rate", form.errors)

    def test_exchange_rate_create_form_invalid_date_format(self):
        """Test create form with invalid date format."""
        form_data = {
            "currency": self.currency.currency_id,
            "rate": "1.25",
            "effective_date": "invalid-date",
            "note": "Test exchange rate",
        }
        form = OrganizationExchangeRateCreateForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("effective_date", form.errors)

    def test_exchange_rate_create_form_save_with_organization(self):
        """Test create form save method with organization context."""
        form_data = {
            "currency": self.currency.currency_id,
            "rate": "1.25",
            "effective_date": "2024-01-01",
            "note": "Test exchange rate",
        }
        form = OrganizationExchangeRateCreateForm(data=form_data)

        self.assertTrue(form.is_valid())

        # Save with organization and member context
        exchange_rate = form.save(commit=False)
        exchange_rate.organization = self.organization
        exchange_rate.added_by = self.member
        exchange_rate.save()

        self.assertIsInstance(exchange_rate, OrganizationExchangeRate)
        self.assertEqual(exchange_rate.organization, self.organization)
        self.assertEqual(exchange_rate.currency, self.currency)
        self.assertEqual(exchange_rate.rate, Decimal("1.25"))
        self.assertEqual(exchange_rate.added_by, self.member)


class TestOrganizationExchangeRateUpdateForm(TestCase):
    """Test OrganizationExchangeRateUpdateForm validation and behavior."""

    def setUp(self):
        self.organization = OrganizationFactory()
        self.member = OrganizationMemberFactory(organization=self.organization)
        self.currency = Currency.objects.create(code="USD", name="US Dollar")
        self.exchange_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            added_by=self.member,
            rate=Decimal("1.25"),
            note="Original note",
        )

    def test_exchange_rate_update_form_inheritance(self):
        """Test that update form inherits from base form."""
        from apps.currencies.forms import BaseExchangeRateUpdateForm

        form = OrganizationExchangeRateUpdateForm()
        self.assertIsInstance(form, BaseExchangeRateUpdateForm)

    def test_exchange_rate_update_form_valid_data(self):
        """Test update form with valid data."""
        form_data = {
            "rate": "1.35",
            "note": "Updated exchange rate",
        }
        form = OrganizationExchangeRateUpdateForm(
            data=form_data, instance=self.exchange_rate
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["rate"], Decimal("1.35"))
        self.assertEqual(form.cleaned_data["note"], "Updated exchange rate")

    def test_exchange_rate_update_form_initialization_with_instance(self):
        """Test update form initialization with existing instance."""
        form = OrganizationExchangeRateUpdateForm(instance=self.exchange_rate)

        # Check initial values
        self.assertEqual(form.initial["rate"], Decimal("1.25"))
        self.assertEqual(form.initial["note"], "Original note")

    def test_exchange_rate_update_form_save_updates_instance(self):
        """Test update form save method updates existing instance."""
        form_data = {
            "rate": "1.45",
            "note": "Final updated note",
        }
        form = OrganizationExchangeRateUpdateForm(
            data=form_data, instance=self.exchange_rate
        )

        self.assertTrue(form.is_valid())
        updated_rate = form.save()

        self.assertEqual(updated_rate.organization_exchange_rate_id, self.exchange_rate.organization_exchange_rate_id)
        self.assertEqual(updated_rate.rate, Decimal("1.45"))
        self.assertEqual(updated_rate.note, "Final updated note")

        # Verify database was updated
        self.exchange_rate.refresh_from_db()
        self.assertEqual(self.exchange_rate.rate, Decimal("1.45"))
        self.assertEqual(self.exchange_rate.note, "Final updated note")

    def test_exchange_rate_update_form_invalid_rate(self):
        """Test update form with invalid rate."""
        form_data = {
            "rate": "-2.50",
            "note": "Updated note",
        }
        form = OrganizationExchangeRateUpdateForm(
            data=form_data, instance=self.exchange_rate
        )

        self.assertFalse(form.is_valid())
        self.assertIn("rate", form.errors)
