from .models import Currency

def get_currency_by_code(code: str) -> Currency:
    return Currency.objects.get(code=code)