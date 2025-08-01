from apps.organizations.models import Organization
from .models import Currency
from apps.workspaces.models import WorkspaceExchangeRate
from apps.organizations.models import OrganizationExchangeRate


def get_currency_by_code(code: str) -> Currency:
    return Currency.objects.get(code=code)


def get_org_defined_currencies(organization: Organization):
    return Currency.objects.filter(
        organizations_organizationexchangerate__organization=organization,
    )


def get_closest_exchanged_rate(*, currency, occurred_at, organization, workspace=None):
    # Get the workspace lvl exchange rate whose effective date is closest to the occurred_at date
    if workspace:
        workspace_exchange_rate = (
            WorkspaceExchangeRate.objects.filter(
                workspace=workspace,
                currency__code=currency.code,
                effective_date__lte=occurred_at,
                is_approved=True,
            )
            .order_by("-effective_date")
            .first()
        )
        if workspace_exchange_rate:
            return workspace_exchange_rate

    # Get the organization lvl exchange rate whose effective date is closest to the occurred_at date
    organization_exchange_rate = (
        OrganizationExchangeRate.objects.filter(
            organization=organization,
            currency__code=currency.code,
            effective_date__lte=occurred_at,
        )
        .order_by("-effective_date")
        .first()
    )

    if organization_exchange_rate:
        return organization_exchange_rate

    return None
