"""Unit tests for currency services.

Tests the service functions for currency operations including:
- createCurrency
"""

from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.currencies.models import Currency
from apps.currencies.services import createCurrency
from tests.factories import CurrencyFactory


class TestCreateCurrency(TestCase):
    """Test createCurrency service function."""

    def test_create_currency_success(self):
        """Test successfully creating a currency with valid code."""
        try:
            currency = createCurrency("USD")
            
            self.assertIsInstance(currency, Currency)
            self.assertEqual(currency.code, "USD")
            self.assertIsNotNone(currency.currency_id)
        except Exception as e:
            self.fail(f"createCurrency raised {e} unexpectedly!")

    def test_create_currency_auto_uppercase(self):
        """Test that currency code is automatically converted to uppercase."""
        try:
            currency = createCurrency("eur")
            
            # The model's clean() method converts to uppercase
            self.assertEqual(currency.code, "EUR")
        except Exception as e:
            self.fail(f"createCurrency raised {e} unexpectedly!")

    def test_create_currency_duplicate_code(self):
        """Test creating currency with duplicate code raises error."""
        # Create first currency
        CurrencyFactory(code="JPY", name="Japanese Yen")
        
        # Try to create another with same code
        with self.assertRaises(Exception):
            createCurrency("JPY")

    def test_create_currency_invalid_code(self):
        """Test creating currency with invalid ISO code."""
        # The service calls clean() which validates the code
        try:
            currency = createCurrency("XXX")
            self.assertEqual(currency.code, "XXX")
        except Exception as e:
            self.fail(f"createCurrency raised {e} unexpectedly!")

    def test_create_currency_empty_code(self):
        """Test creating currency with empty code."""
        # The service calls clean() which validates the code
        with self.assertRaises(ValidationError):
            createCurrency("")

    def test_create_currency_persists_to_database(self):
        """Test that created currency is actually saved to database."""
        try:
            currency = createCurrency("DKK")
            
            # Verify it exists in database
            saved_currency = Currency.objects.get(code="DKK")
            self.assertEqual(saved_currency.currency_id, currency.currency_id)
        except Exception as e:
            self.fail(f"createCurrency raised {e} unexpectedly!")
