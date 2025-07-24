from django.shortcuts import get_object_or_404
from apps.organizations.models import OrganizationExchangeRate
from typing import Any


class OrganizationExchangeRateRequiredMixin:
    exchange_rate = None
    instance = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        org_exchange_rate_id = kwargs.get("pk")
        self.exchange_rate = get_object_or_404(
            OrganizationExchangeRate,
            pk=org_exchange_rate_id,
            organization=self.organization,
        )
        self.instance = self.exchange_rate
        print(f"Update org_exchange_rate note: {self.instance.note}")

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["exchange_rate"] = self.exchange_rate
        return context
