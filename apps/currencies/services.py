from .models import Currency

def createCurrency(code: str):
    currency = Currency.objects.create(code=code)
    return currency