import factory
from factory.django import DjangoModelFactory
from apps.currencies.models import Currency

# Common ISO4217 currency codes
CURRENCY_CODES = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY"]


class CurrencyFactory(DjangoModelFactory):
    """Factory for creating Currency instances."""

    class Meta:
        model = Currency

    code = factory.Iterator(CURRENCY_CODES)  # cycles through common ISO4217 codes
    name = None  # Will be automatically set in the model's clean() method
