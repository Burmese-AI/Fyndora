from typing import Any

from django.shortcuts import get_object_or_404
from django.db.models import QuerySet
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.organizations.selectors import get_user_org_membership
from apps.organizations.models import Organization

from ..models import Entry
from ..selectors import get_org_entries
from ..constants import DETAIL_CONTEXT_OBJECT_NAME


class OrganizationRequiredMixin:
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

class EntryRequiredMixin(OrganizationMemberRequiredMixin):
    entry = None
    attachments = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        entry_id = kwargs.get("pk")
        self.entry = get_object_or_404(Entry, pk=entry_id)
        self.attachments = self.entry.attachments.all()

class HtmxOobResponseMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            context["is_oob"] = True
        return context

class OrganizationContextMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if hasattr(self, "organization"):
            # To create a new org_exp entry, organization is required in the form template
            context["organization"] = self.organization
        if hasattr(self, "org_member"):
            context["org_member"] = self.org_member
        if hasattr(self, "org_exp_entry"):
            context["entry"] = self.org_exp_entry
        if hasattr(self, "attachments"):
            context["attachments"] = self.attachments
        return context


class EntryDetailView(
    LoginRequiredMixin, EntryRequiredMixin, OrganizationContextMixin, DetailView
):
    model = Entry
    template_name = "entries/components/detail_modal.html"
    context_object_name = DETAIL_CONTEXT_OBJECT_NAME

    def get_queryset(self) -> QuerySet[Any]:
        return get_org_entries(
            organization=self.organization, prefetch_attachments=True
        )