from django.shortcuts import get_object_or_404
from apps.organizations.selectors import get_user_org_membership
from apps.organizations.models import Organization
from ..models import Entry
from typing import Any


class OrganizationRequiredMixin():
    organization = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        organization_id = kwargs.get("organization_id")
        self.organization = get_object_or_404(Organization, pk=organization_id)

class OrganizationMemberRequiredMixin(OrganizationRequiredMixin):
    org_member = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)  # Ensures organization is set
        self.org_member = get_user_org_membership(self.request.user, self.organization)

class OrganizationExpenseEntryRequiredMixin(OrganizationMemberRequiredMixin):
    org_exp_entry = None
    attachments = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        org_exp_entry_id = kwargs.get("pk")
        self.org_exp_entry = get_object_or_404(Entry, pk=org_exp_entry_id)
        self.attachments = self.org_exp_entry.attachments.all()
    
class HtmxOobResponseMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            context["is_oob"] = True
        return context
    