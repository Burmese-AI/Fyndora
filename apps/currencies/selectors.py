from apps.organizations.models import Organization
from .models import Currency


def get_currency_by_code(code: str) -> Currency:
    return Currency.objects.get(
        code=code
    )

def get_org_defined_currencies(organization: Organization):
    return Currency.objects.filter(
        organizations_organizationexchangerate__organization=organization,
    )