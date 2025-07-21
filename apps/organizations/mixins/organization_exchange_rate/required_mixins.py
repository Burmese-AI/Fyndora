from django.shortcuts import get_object_or_404
from apps.organizations.models import OrganizationExchangeRate

class OrganizationExchangeRateRequiredMixin():
    org_exchange_rate = None
    instance = None
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        org_exchange_rate_id = kwargs.get("pk")
        self.org_exchange_rate = get_object_or_404(OrganizationExchangeRate, pk=org_exchange_rate_id, organization=self.organization)
        self.instance = self.org_exchange_rate
        print(f"Update org_exchange_rate note: {self.instance.note}")
