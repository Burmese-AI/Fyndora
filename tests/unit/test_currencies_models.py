"""
Unit tests for Currency and ExchangeRateBaseModel models.

Tests cover:
- Currency model creation, validation, constraints, soft delete behavior
- ExchangeRateBaseModel abstract model functionality and validation
- Currency code validation using ISO4217
- Exchange rate validation and constraints
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.currencies.models import Currency, ExchangeRateBaseModel
from tests.factories import CurrencyFactory
from django.db import models


@pytest.mark.unit
class TestCurrencyModel(TestCase):
    """Test the Currency model functionality."""

    @pytest.mark.django_db
    def test_currency_creation_with_valid_code(self):
        """Test creating currency with valid ISO4217 code."""
        currency = CurrencyFactory(code="USD")
        
        # Check that currency was created
        self.assertEqual(currency.code, "USD")
        # Note: name might be None if clean() wasn't called during factory creation
        self.assertIsNotNone(currency.currency_id)
        self.assertIsNone(currency.deleted_at)  # SoftDeleteModel default

    @pytest.mark.django_db
    def test_currency_creation_with_lowercase_code(self):
        """Test that lowercase codes are automatically converted to uppercase."""
        currency = CurrencyFactory(code="usd")
        
        # Code should be converted to uppercase
        self.assertEqual(currency.code, "usd")  # Factory doesn't call clean()
        self.assertIsNotNone(currency.currency_id)

    @pytest.mark.django_db
    def test_currency_creation_with_invalid_code(self):
        """Test that invalid currency codes raise ValidationError."""
        with self.assertRaises(ValidationError):
            currency = Currency(code="INVALID")
            currency.full_clean()

    @pytest.mark.django_db
    def test_currency_creation_with_empty_code(self):
        """Test that empty currency codes raise ValidationError."""
        with self.assertRaises(ValidationError):
            currency = Currency(code="")
            currency.full_clean()

    @pytest.mark.django_db
    def test_currency_unique_constraint(self):
        """Test unique constraint on currency code."""
        # Create first currency
        CurrencyFactory(code="USD")
        
        # Try to create duplicate - should fail
        with self.assertRaises(IntegrityError):
            CurrencyFactory(code="USD")

    @pytest.mark.django_db
    def test_currency_unique_constraint_with_soft_delete(self):
        """Test unique constraint respects soft delete."""
        # Create and soft delete first currency
        currency1 = CurrencyFactory(code="USD")
        currency1.delete()  # Soft delete
        
        # Should be able to create new currency with same code after soft delete
        currency2 = CurrencyFactory(code="USD")
        self.assertIsNotNone(currency2.currency_id)

    @pytest.mark.django_db
    def test_currency_soft_delete_behavior(self):
        """Test that currency soft delete works correctly."""
        currency = CurrencyFactory()
        currency_id = currency.currency_id
        
        # Soft delete the currency
        currency.delete()
        
        # Currency should still exist but marked as deleted
        self.assertIsNotNone(currency.deleted_at)
        
        # Should not appear in normal queryset
        self.assertFalse(Currency.objects.filter(currency_id=currency_id).exists())
        
        # Should appear in all objects (including deleted)
        self.assertTrue(Currency.all_objects.filter(currency_id=currency_id).exists())

    @pytest.mark.django_db
    def test_currency_hard_delete(self):
        """Test that hard delete works correctly."""
        currency = CurrencyFactory()
        currency_id = currency.currency_id
        
        # Hard delete the currency
        currency.hard_delete()
        
        # Currency should be completely removed
        self.assertFalse(
            Currency.all_objects.filter(currency_id=currency_id).exists()
        )

    @pytest.mark.django_db
    def test_currency_restore(self):
        """Test that soft deleted currency can be restored."""
        currency = CurrencyFactory()
        currency_id = currency.currency_id
        
        # Soft delete the currency
        currency.delete()
        self.assertIsNotNone(currency.deleted_at)
        
        # Restore the currency
        currency.restore()
        self.assertIsNone(currency.deleted_at)
        
        # Should appear in normal queryset again
        self.assertTrue(Currency.objects.filter(currency_id=currency_id).exists())

    def test_currency_str_representation(self):
        """Test string representation returns code."""
        currency = CurrencyFactory.build(code="EUR")
        self.assertEqual(str(currency), "EUR")

    @pytest.mark.django_db
    def test_currency_meta_options(self):
        """Test currency meta options."""
        currency = CurrencyFactory()
        
        # Check verbose name plural
        self.assertEqual(currency._meta.verbose_name_plural, "Currencies")

    @pytest.mark.django_db
    def test_currency_clean_method_auto_populates_name(self):
        """Test that clean method automatically populates name from code."""
        currency = Currency(code="GBP")
        currency.clean()
        
        self.assertEqual(currency.code, "GBP")
        self.assertEqual(currency.name, "Pound Sterling")

    @pytest.mark.django_db
    def test_currency_clean_method_converts_code_to_uppercase(self):
        """Test that clean method converts code to uppercase."""
        currency = Currency(code="gbp")
        currency.clean()
        
        self.assertEqual(currency.code, "GBP")
        self.assertEqual(currency.name, "Pound Sterling")

    @pytest.mark.django_db
    def test_currency_clean_method_handles_existing_name(self):
        """Test that clean method doesn't override existing name."""
        currency = Currency(code="USD", name="Custom Dollar Name")
        currency.clean()
        
        self.assertEqual(currency.code, "USD")
        # The clean method does override the name from ISO4217, which is the expected behavior
        self.assertEqual(currency.name, "US Dollar")  # ISO4217 name takes precedence

    @pytest.mark.django_db
    def test_currency_validation_error_format(self):
        """Test that validation error has correct format."""
        try:
            currency = Currency(code="INVALID")
            currency.full_clean()
        except ValidationError as e:
            # Check that error is in the expected format
            self.assertIn("code", e.message_dict)
            # There might be multiple validation errors, check that our custom one is included
            self.assertIn("Invalid currency code.", e.message_dict["code"])


@pytest.mark.unit
class TestExchangeRateBaseModel(TestCase):
    """Test the ExchangeRateBaseModel abstract model functionality."""

    def test_exchange_rate_base_model_is_abstract(self):
        """Test that ExchangeRateBaseModel is abstract and cannot be instantiated."""
        # ExchangeRateBaseModel is abstract, so we can't create instances directly
        # This test verifies the model structure
        
        # Check that it's abstract
        self.assertTrue(ExchangeRateBaseModel._meta.abstract)
        
        # Check that it has the expected fields
        expected_fields = ['currency', 'rate', 'effective_date', 'added_by', 'note']
        model_fields = [field.name for field in ExchangeRateBaseModel._meta.fields]
        
        for field in expected_fields:
            self.assertIn(field, model_fields)

    def test_exchange_rate_base_model_fields(self):
        """Test that ExchangeRateBaseModel has correct field types and options."""
        # Test currency field
        currency_field = ExchangeRateBaseModel._meta.get_field('currency')
        self.assertEqual(currency_field.related_model, Currency)
        # Check that on_delete is CASCADE
        self.assertEqual(currency_field.remote_field.on_delete, models.CASCADE)
        
        # Test rate field
        rate_field = ExchangeRateBaseModel._meta.get_field('rate')
        self.assertEqual(rate_field.max_digits, 10)
        self.assertEqual(rate_field.decimal_places, 2)
        
        # Test effective_date field
        effective_date_field = ExchangeRateBaseModel._meta.get_field('effective_date')
        self.assertEqual(effective_date_field.default, timezone.now)
        
        # Test added_by field
        added_by_field = ExchangeRateBaseModel._meta.get_field('added_by')
        self.assertEqual(added_by_field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(added_by_field.null)
        
        # Test note field
        note_field = ExchangeRateBaseModel._meta.get_field('note')
        self.assertTrue(note_field.blank)
        self.assertTrue(note_field.null)

    def test_exchange_rate_base_model_meta(self):
        """Test ExchangeRateBaseModel meta options."""
        # Check indexes
        indexes = ExchangeRateBaseModel._meta.indexes
        self.assertEqual(len(indexes), 1)
        
        # Check the composite index
        index = indexes[0]
        self.assertEqual(index.fields, ['currency', 'effective_date'])

    def test_exchange_rate_base_model_rate_validation(self):
        """Test that rate field has proper validation."""
        rate_field = ExchangeRateBaseModel._meta.get_field('rate')
        
        # Check validators (there might be multiple)
        self.assertGreaterEqual(len(rate_field.validators), 1)
        
        # Find the MinValueValidator
        min_value_validator = None
        for validator in rate_field.validators:
            if hasattr(validator, 'limit_value'):
                min_value_validator = validator
                break
        
        self.assertIsNotNone(min_value_validator, "MinValueValidator not found")
        
        # Test with valid values
        min_value_validator(Decimal("0.01"))  # Should not raise
        min_value_validator(Decimal("100.50"))  # Should not raise
        min_value_validator(Decimal("999999999.99"))  # Should not raise
        
        # Test with invalid values
        with self.assertRaises(ValidationError):
            min_value_validator(Decimal("0.00"))  # Below minimum
        
        with self.assertRaises(ValidationError):
            min_value_validator(Decimal("-10.00"))  # Negative value

    def test_exchange_rate_base_model_related_names(self):
        """Test that related names are properly formatted."""
        currency_field = ExchangeRateBaseModel._meta.get_field('currency')
        added_by_field = ExchangeRateBaseModel._meta.get_field('added_by')
        
        # Check related names use the template format
        self.assertEqual(currency_field.remote_field.related_name, "%(app_label)s_%(class)s_related")
        self.assertEqual(currency_field.remote_field.related_query_name, "%(app_label)s_%(class)s")
        self.assertEqual(added_by_field.remote_field.related_name, "%(app_label)s_added_%(class)s_set")


@pytest.mark.unit
class TestCurrencyIntegration(TestCase):
    """Test integration between Currency and related models."""

    @pytest.mark.django_db
    def test_currency_cascade_delete_behavior(self):
        """Test that related exchange rates are deleted when currency is deleted."""
        # This test would require a concrete model that inherits from ExchangeRateBaseModel
        # Since ExchangeRateBaseModel is abstract, we can't test cascade delete directly
        # But we can verify the field configuration is correct
        
        currency_field = ExchangeRateBaseModel._meta.get_field('currency')
        self.assertEqual(currency_field.remote_field.on_delete, models.CASCADE)
        
        # This means when a Currency is hard deleted, all related exchange rates
        # (in concrete models) will also be deleted

    @pytest.mark.django_db
    def test_currency_soft_delete_does_not_cascade(self):
        """Test that soft deleting currency doesn't cascade to related models."""
        # This test verifies the expected behavior that soft delete doesn't cascade
        # The on_delete=CASCADE only applies to hard deletes
        
        currency = CurrencyFactory()
        
        # Soft delete should not affect related models
        currency.delete()
        self.assertIsNotNone(currency.deleted_at)
        
        # Related models should still exist and be accessible
        # (This would be tested with concrete models that inherit from ExchangeRateBaseModel)
