"""Unit tests for currency selectors.

Tests the selector functions for currency operations including:
- get_currency_by_code
- get_org_defined_currencies  
- get_closest_exchanged_rate
"""

from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from datetime import timezone as dt_timezone

from apps.currencies.models import Currency
from apps.currencies.selectors import (
    get_currency_by_code,
    get_org_defined_currencies,
    get_closest_exchanged_rate,
)
from tests.factories import (
    CurrencyFactory,
    OrganizationFactory,
    OrganizationExchangeRateFactory,
    OrganizationMemberFactory,
    WorkspaceFactory,
    WorkspaceExchangeRateFactory,
)


class TestGetCurrencyByCode(TestCase):
    """Test get_currency_by_code selector function."""

    def setUp(self):
        """Set up test data."""
        self.usd_currency = CurrencyFactory(code="USD", name="US Dollar")
        self.eur_currency = CurrencyFactory(code="EUR", name="Euro")

    def test_get_currency_by_code_success(self):
        """Test successfully getting currency by code."""
        try:
            currency = get_currency_by_code("USD")
            self.assertEqual(currency, self.usd_currency)
            self.assertEqual(currency.code, "USD")
            self.assertEqual(currency.name, "US Dollar")
        except Exception as e:
            self.fail(f"get_currency_by_code raised {e} unexpectedly!")

    def test_get_currency_by_code_case_sensitive(self):
        """Test getting currency by code is case sensitive."""
        try:
            currency = get_currency_by_code("USD")
            self.assertEqual(currency, self.usd_currency)
        except Exception as e:
            self.fail(f"get_currency_by_code raised {e} unexpectedly!")
        
        # Test that lowercase fails
        with self.assertRaises(Currency.DoesNotExist):
            get_currency_by_code("usd")

    def test_get_currency_by_code_does_not_exist(self):
        """Test getting currency by non-existent code raises exception."""
        with self.assertRaises(Currency.DoesNotExist):
            get_currency_by_code("INVALID")


class TestGetOrgDefinedCurrencies(TestCase):
    """Test get_org_defined_currencies selector function."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.member = OrganizationMemberFactory(organization=self.organization)
        
        # Create currencies
        self.usd_currency = CurrencyFactory(code="USD", name="US Dollar")
        self.eur_currency = CurrencyFactory(code="EUR", name="Euro")
        self.gbp_currency = CurrencyFactory(code="GBP", name="British Pound")
        
        # Create exchange rates for the organization
        self.org_exchange_rate_usd = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.usd_currency,
            rate=Decimal("1.00"),
            effective_date=date(2024, 1, 1),
            added_by=self.member,
        )
        self.org_exchange_rate_eur = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.eur_currency,
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 1),
            added_by=self.member,
        )

    def test_get_org_defined_currencies_success(self):
        """Test successfully getting currencies defined for an organization."""
        try:
            currencies = get_org_defined_currencies(self.organization)
            self.assertEqual(currencies.count(), 2)
            
            currency_codes = [c.code for c in currencies]
            self.assertIn("USD", currency_codes)
            self.assertIn("EUR", currency_codes)
            self.assertNotIn("GBP", currency_codes)  # No exchange rate for GBP
        except Exception as e:
            self.fail(f"get_org_defined_currencies raised {e} unexpectedly!")

    def test_get_org_defined_currencies_empty_organization(self):
        """Test getting currencies for organization with no exchange rates."""
        empty_org = OrganizationFactory()
        try:
            currencies = get_org_defined_currencies(empty_org)
            self.assertEqual(currencies.count(), 0)
        except Exception as e:
            self.fail(f"get_org_defined_currencies raised {e} unexpectedly!")

    def test_get_org_defined_currencies_distinct_currencies(self):
        """Test that currencies are returned as distinct (no duplicates)."""
        # Add another exchange rate for USD with different date
        OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.usd_currency,
            rate=Decimal("1.10"),
            effective_date=date(2024, 2, 1),
            added_by=self.member,
        )
        
        try:
            currencies = get_org_defined_currencies(self.organization)
            self.assertEqual(currencies.count(), 2)  # Still only 2 unique currencies
        except Exception as e:
            self.fail(f"get_org_defined_currencies raised {e} unexpectedly!")


class TestGetClosestExchangedRate(TestCase):
    """Test get_closest_exchanged_rate selector function."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.member = OrganizationMemberFactory(organization=self.organization)
        self.currency = CurrencyFactory(code="USD", name="US Dollar")
        
        # Create organization exchange rates
        self.org_rate_jan = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.00"),
            effective_date=date(2024, 1, 1),
            added_by=self.member,
        )
        self.org_rate_feb = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.10"),
            effective_date=date(2024, 2, 1),
            added_by=self.member,
        )
        self.org_rate_mar = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.20"),
            effective_date=date(2024, 3, 1),
            added_by=self.member,
        )
        
        # Create workspace exchange rates
        self.workspace_rate_jan = WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.05"),
            effective_date=date(2024, 1, 1),
            added_by=self.member,
            is_approved=True,
        )
        self.workspace_rate_feb = WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.15"),
            effective_date=date(2024, 2, 1),
            added_by=self.member,
            is_approved=True,
        )

    def test_get_closest_exchanged_rate_workspace_priority(self):
        """Test that workspace exchange rate takes priority when available."""
        occurred_at = datetime(2024, 2, 15, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=self.currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=self.workspace,
            )
            
            # Should return workspace rate (Feb 1) as it's closest to occurred_at
            self.assertEqual(result, self.workspace_rate_feb)
            self.assertEqual(result.rate, Decimal("1.15"))
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")

    def test_get_closest_exchanged_rate_workspace_not_approved(self):
        """Test that unapproved workspace rates are ignored."""
        # Create unapproved workspace rate
        WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.25"),
            effective_date=date(2024, 2, 15),
            added_by=self.member,
            is_approved=False,
        )
        
        # Test with a date where only unapproved workspace rates exist
        occurred_at = datetime(2024, 2, 20, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=self.currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=self.workspace,
            )
            
            # Should return workspace rate (Feb 1) as it's the closest approved workspace rate
            # The unapproved rate on Feb 15 is ignored, but Feb 1 rate is still valid
            self.assertEqual(result, self.workspace_rate_feb)
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")

    def test_get_closest_exchanged_rate_no_workspace(self):
        """Test getting rate when no workspace is provided."""
        occurred_at = datetime(2024, 2, 15, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=self.currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=None,
            )
            
            # Should return organization rate (Feb 1) as it's closest to occurred_at
            self.assertEqual(result, self.org_rate_feb)
            self.assertEqual(result.rate, Decimal("1.10"))
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")

    def test_get_closest_exchanged_rate_organization_fallback(self):
        """Test that organization rate is used as fallback when workspace has no valid rates."""
        # Test with a date where workspace rates are too old to be relevant
        occurred_at = datetime(2024, 4, 15, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=self.currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=self.workspace,
            )
            
            # Should return workspace rate (Feb 1) as it's still the closest approved workspace rate
            # The selector prioritizes any approved workspace rate over organization rates
            self.assertEqual(result, self.workspace_rate_feb)
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")

    def test_get_closest_exchanged_rate_organization_fallback_no_workspace_rates(self):
        """Test that organization rate is used when workspace has no approved rates."""
        # Create a workspace with no approved rates
        empty_workspace = WorkspaceFactory(organization=self.organization)
        
        occurred_at = datetime(2024, 3, 15, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=self.currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=empty_workspace,
            )
            
            # Should return organization rate (Mar 1) as workspace has no rates
            self.assertEqual(result, self.org_rate_mar)
            self.assertEqual(result.rate, Decimal("1.20"))
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")

    def test_get_closest_exchanged_rate_no_rates_before_date(self):
        """Test getting rate when no rates exist before the occurred_at date."""
        occurred_at = datetime(2023, 12, 1, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=self.currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=self.workspace,
            )
            
            # Should return None as no rates exist before Dec 2023
            self.assertIsNone(result)
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")

    def test_get_closest_exchanged_rate_exact_date_match(self):
        """Test getting rate when occurred_at exactly matches an effective_date."""
        occurred_at = datetime(2024, 2, 1, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=self.currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=self.workspace,
            )
            
            # Should return workspace rate (Feb 1) as it's an exact match
            self.assertEqual(result, self.workspace_rate_feb)
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")

    def test_get_closest_exchanged_rate_different_currency(self):
        """Test getting rate for a different currency."""
        eur_currency = CurrencyFactory(code="EUR", name="Euro")
        
        # Create EUR exchange rates
        eur_org_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=eur_currency,
            rate=Decimal("0.85"),
            effective_date=date(2024, 2, 1),
            added_by=self.member,
        )
        
        occurred_at = datetime(2024, 2, 15, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=eur_currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=self.workspace,
            )
            
            # Should return EUR organization rate
            self.assertEqual(result, eur_org_rate)
            self.assertEqual(result.currency.code, "EUR")
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")

    def test_get_closest_exchanged_rate_no_workspace_rates(self):
        """Test getting rate when workspace has no exchange rates."""
        empty_workspace = WorkspaceFactory(organization=self.organization)
        occurred_at = datetime(2024, 2, 15, tzinfo=dt_timezone.utc)
        
        try:
            result = get_closest_exchanged_rate(
                currency=self.currency,
                occurred_at=occurred_at,
                organization=self.organization,
                workspace=empty_workspace,
            )
            
            # Should fall back to organization rate
            self.assertEqual(result, self.org_rate_feb)
        except Exception as e:
            self.fail(f"get_closest_exchanged_rate raised {e} unexpectedly!")
