from .models import Currency


def createCurrency(code: str):
    currency = Currency.objects.create(code=code)
    # require clean () to generate the code.name(THA)
    currency.clean()
    currency.save()
    return currency
