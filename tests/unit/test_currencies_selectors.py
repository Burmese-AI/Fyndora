"""
Unit tests for apps.currencies.selectors
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ObjectDoesNotExist
from unittest.mock import patch

from apps.currencies.models import Currency
from apps.currencies.selectors import (
    get_currency_by_code,
    get_or_create_currency_by_code,
    get_org_defined_currencies,
    get_closest_exchanged_rate,
)
from tests.factories import (
    CurrencyFactory,
    OrganizationFactory,
    OrganizationExchangeRateFactory,
    WorkspaceFactory,
    WorkspaceExchangeRateFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestGetCurrencyByCode:
    def test_get_currency_by_code_success(self):
        """Test getting currency by code successfully."""
        currency = CurrencyFactory(code="USD")

        result = get_currency_by_code("USD")

        assert result == currency
        assert result.code == "USD"

    def test_get_currency_by_code_not_found(self):
        """Test getting currency by code when not found."""
        result = get_currency_by_code("INVALID")
        assert result is None

    def test_get_currency_by_code_case_sensitive(self):
        """Test that currency code lookup is case sensitive."""
        CurrencyFactory(code="USD")

        result = get_currency_by_code("usd")
        assert result is None


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrCreateCurrencyByCode:
    def test_get_existing_currency(self):
        """Test getting existing currency without creating new one."""
        currency = CurrencyFactory(code="USD")

        with patch("apps.currencies.selectors.get_currency_by_code") as mock_get:
            mock_get.return_value = currency

            result = get_or_create_currency_by_code("USD")

            assert result == currency
            mock_get.assert_called_once_with("USD")

    def test_create_currency_when_not_found(self):
        """Test creating currency when not found."""
        with patch("apps.currencies.selectors.get_currency_by_code") as mock_get:
            mock_get.return_value = None

            with patch("apps.currencies.selectors.createCurrency") as mock_create:
                mock_currency = CurrencyFactory(code="EUR")
                mock_create.return_value = mock_currency

                result = get_or_create_currency_by_code("EUR")

                assert result == mock_currency
                mock_get.assert_called_once_with("EUR")
                mock_create.assert_called_once_with("EUR")

    def test_create_currency_when_does_not_exist_exception(self):
        """Test that get_or_create_currency_by_code raises DoesNotExist when currency not found."""
        with patch("apps.currencies.selectors.get_currency_by_code") as mock_get:
            mock_get.side_effect = ObjectDoesNotExist()

            # The function doesn't handle the exception, so it should propagate
            with pytest.raises(ObjectDoesNotExist):
                get_or_create_currency_by_code("GBP")


@pytest.mark.unit
@pytest.mark.django_db
class TestGetOrgDefinedCurrencies:
    def test_get_org_defined_currencies_success(self):
        """Test getting currencies defined for an organization."""
        organization = OrganizationFactory()
        currency1 = CurrencyFactory(code="USD")
        currency2 = CurrencyFactory(code="EUR")
        currency3 = CurrencyFactory(code="GBP")

        # Create exchange rates for organization
        OrganizationExchangeRateFactory(
            organization=organization, currency=currency1, rate=Decimal("1.0")
        )
        OrganizationExchangeRateFactory(
            organization=organization, currency=currency2, rate=Decimal("0.85")
        )
        # currency3 has no exchange rate for this organization

        result = get_org_defined_currencies(organization)

        assert result.count() == 2
        assert currency1 in result
        assert currency2 in result
        assert currency3 not in result

    def test_get_org_defined_currencies_empty(self):
        """Test getting currencies when organization has none defined."""
        organization = OrganizationFactory()

        result = get_org_defined_currencies(organization)

        assert result.count() == 0

    def test_get_org_defined_currencies_distinct(self):
        """Test that duplicate currencies are not returned."""
        organization = OrganizationFactory()
        currency = CurrencyFactory(code="USD")

        # Create multiple exchange rates for same currency
        OrganizationExchangeRateFactory(
            organization=organization,
            currency=currency,
            rate=Decimal("1.0"),
            effective_date=date.today(),
        )
        OrganizationExchangeRateFactory(
            organization=organization,
            currency=currency,
            rate=Decimal("1.1"),
            effective_date=date.today() - timedelta(days=1),
        )

        result = get_org_defined_currencies(organization)

        assert result.count() == 1
        assert currency in result


@pytest.mark.unit
@pytest.mark.django_db
class TestGetClosestExchangedRate:
    def setup_method(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.currency = CurrencyFactory(code="USD")
        self.occurred_at = date.today()

    def test_get_workspace_exchange_rate_when_available(self):
        """Test getting workspace exchange rate when available."""
        workspace_rate = WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at,
            is_approved=True,
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result == workspace_rate

    def test_get_workspace_exchange_rate_closest_date(self):
        """Test getting workspace exchange rate with closest effective date."""
        # Create rates with different dates
        WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("0.9"),
            effective_date=self.occurred_at - timedelta(days=10),
            is_approved=True,
        )
        closest_rate = WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at - timedelta(days=1),
            is_approved=True,
        )
        WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.1"),
            effective_date=self.occurred_at + timedelta(days=1),
            is_approved=True,
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result == closest_rate

    def test_get_workspace_exchange_rate_only_approved(self):
        """Test that only approved workspace exchange rates are returned."""
        # Create unapproved rate
        WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at,
            is_approved=False,
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result is None

    def test_fallback_to_organization_rate_when_no_workspace_rate(self):
        """Test falling back to organization rate when no workspace rate."""
        org_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at,
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result == org_rate

    def test_fallback_to_organization_rate_when_workspace_none(self):
        """Test using organization rate when workspace is None."""
        org_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at,
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=None,
        )

        assert result == org_rate

    def test_get_organization_rate_closest_date(self):
        """Test getting organization rate with closest effective date."""
        # Create rates with different dates
        OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("0.9"),
            effective_date=self.occurred_at - timedelta(days=10),
        )
        closest_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at - timedelta(days=1),
        )
        OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.1"),
            effective_date=self.occurred_at + timedelta(days=1),
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=None,
        )

        assert result == closest_rate

    def test_return_none_when_no_rates_available(self):
        """Test returning None when no exchange rates are available."""
        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result is None

    def test_workspace_rate_takes_precedence_over_org_rate(self):
        """Test that workspace rate takes precedence over organization rate."""
        org_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at,
        )
        workspace_rate = WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.1"),
            effective_date=self.occurred_at,
            is_approved=True,
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result == workspace_rate
        assert result != org_rate

    def test_workspace_rate_future_date_fallback_to_org(self):
        """Test that future workspace rates fall back to organization rate."""
        org_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at,
        )
        WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.1"),
            effective_date=self.occurred_at + timedelta(days=1),
            is_approved=True,
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result == org_rate

    def test_workspace_rate_unapproved_fallback_to_org(self):
        """Test that unapproved workspace rates fall back to organization rate."""
        org_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=self.currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at,
        )
        WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=self.currency,
            rate=Decimal("1.1"),
            effective_date=self.occurred_at,
            is_approved=False,
        )

        result = get_closest_exchanged_rate(
            currency=self.currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result == org_rate

    def test_different_currency_codes(self):
        """Test that currency code filtering works correctly."""
        # Use existing currencies or create with unique codes
        eur_currency = Currency.objects.get_or_create(
            code="EUR", defaults={"name": "Euro"}
        )[0]
        usd_currency = Currency.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar"}
        )[0]

        # Create rates for different currencies
        eur_workspace_rate = WorkspaceExchangeRateFactory(
            workspace=self.workspace,
            currency=eur_currency,
            rate=Decimal("0.85"),
            effective_date=self.occurred_at,
            is_approved=True,
        )
        usd_org_rate = OrganizationExchangeRateFactory(
            organization=self.organization,
            currency=usd_currency,
            rate=Decimal("1.0"),
            effective_date=self.occurred_at,
        )

        # Query for USD currency
        result = get_closest_exchanged_rate(
            currency=usd_currency,
            occurred_at=self.occurred_at,
            organization=self.organization,
            workspace=self.workspace,
        )

        assert result == usd_org_rate
        assert result != eur_workspace_rate
