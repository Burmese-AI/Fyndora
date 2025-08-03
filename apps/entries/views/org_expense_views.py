from typing import Any

from django.db.models.query import QuerySet
from django.http.response import HttpResponse as HttpResponse
from django.urls import reverse

from apps.core.utils import permission_denied_view
from apps.core.views.base_views import BaseGetModalFormView
from apps.core.views.crud_base_views import (
    BaseCreateView,
    BaseDeleteView,
    BaseListView,
    BaseUpdateView,
)
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
)
from apps.core.views.service_layer_mixins import (
    HtmxRowResponseMixin,
    HtmxTableServiceMixin,
)

from ..constants import CONTEXT_OBJECT_NAME, EntryStatus, EntryType
from ..forms import (
    BaseUpdateEntryForm,
    CreateOrganizationExpenseEntryForm,
)
from ..models import Entry
from ..selectors import get_entries
from ..services import create_entry_with_attachments, delete_entry
from ..utils import (
    can_add_org_expense,
    can_delete_org_expense,
    can_update_org_expense,
    can_view_org_expense,
)
from .base_views import (
    OrganizationLevelEntryView,
)
from .mixins import (
    EntryFormMixin,
    EntryRequiredMixin,
)


class OrganizationExpenseListView(
    OrganizationRequiredMixin,
    OrganizationLevelEntryView,
    BaseListView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"
    template_name = "entries/index.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_view_org_expense(request.user, self.organization):
            return permission_denied_view(
                request,
                "You do not have permission to view organization expenses.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            organization=self.organization,
            entry_types=[EntryType.ORG_EXP],
            annotate_attachment_count=True,
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["permissions"] = {
            "can_add_org_expense": can_add_org_expense(
                self.request.user, self.organization
            ),
        }
        if not self.request.htmx:
            pass
            # context["stats"] = get_org_expense_stats(self.organization)
        return context


class OrganizationExpenseCreateView(
    OrganizationRequiredMixin,
    OrganizationLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    HtmxTableServiceMixin,
    BaseCreateView,
):
    model = Entry
    form_class = CreateOrganizationExpenseEntryForm
    modal_template_name = "entries/components/create_modal.html"
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_add_org_expense(request.user, self.organization):
            return permission_denied_view(
                request,
                "You do not have permission to add organization expenses.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            entry_types=[EntryType.ORG_EXP],
            annotate_attachment_count=True,
        )

    def get_modal_title(self) -> str:
        return "Organization Expense"

    def get_post_url(self) -> str:
        return reverse(
            "organization_expense_create",
            kwargs={"organization_id": self.organization.pk},
        )

    def perform_service(self, form):
        # print("🧼 Cleaned Data:", form.cleaned_data)  # TEMP DEBUG
        create_entry_with_attachments(
            amount=form.cleaned_data["amount"],
            occurred_at=form.cleaned_data["occurred_at"],
            description=form.cleaned_data["description"],
            attachments=form.cleaned_data["attachment_files"],
            entry_type=EntryType.ORG_EXP,
            organization=self.organization,
            currency=form.cleaned_data["currency"],
            submitted_by_org_member=self.org_member,
            user=self.request.user,
            request=self.request,
        )


class OrganizationExpenseUpdateView(
    OrganizationRequiredMixin,
    EntryRequiredMixin,
    OrganizationLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    HtmxRowResponseMixin,
    BaseUpdateView,
):
    model = Entry
    form_class = BaseUpdateEntryForm
    modal_template_name = "entries/components/update_modal.html"
    row_template_name = "entries/partials/row.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_update_org_expense(request.user, self.organization):
            return permission_denied_view(
                request,
                "You do not have permission to update organization expenses.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Entry.objects.filter(
            organization=self.organization,
            entry_type=EntryType.ORG_EXP,
            entry_id=self.kwargs["pk"],
        )

    def get_modal_title(self) -> str:
        return "Organization Expense"

    def get_post_url(self) -> str:
        return reverse(
            "organization_expense_update",
            kwargs={"organization_id": self.organization.pk, "pk": self.instance.pk},
        )

    def perform_service(self, form):
        from ..services import update_entry_status, update_entry_user_inputs

        if self.entry.status == EntryStatus.PENDING:
            update_entry_user_inputs(
                entry=self.entry,
                organization=self.organization,
                amount=form.cleaned_data["amount"],
                occurred_at=form.cleaned_data["occurred_at"],
                description=form.cleaned_data["description"],
                currency=form.cleaned_data["currency"],
                attachments=form.cleaned_data["attachment_files"],
                replace_attachments=True,
                user=self.request.user,
                request=self.request,
            )

        # If the status has changed, update the status
        if self.entry.status != form.cleaned_data["status"]:
            update_entry_status(
                entry=self.entry,
                status=form.cleaned_data["status"],
                last_status_modified_by=self.org_member,
                status_note=form.cleaned_data["status_note"],
            )


class OrganizationExpenseDeleteView(
    OrganizationRequiredMixin,
    EntryRequiredMixin,
    OrganizationLevelEntryView,
    HtmxTableServiceMixin,
    BaseDeleteView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_delete_org_expense(request.user, self.organization):
            return permission_denied_view(
                request,
                "You do not have permission to delete organization expenses.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            entry_types=[EntryType.ORG_EXP],
            annotate_attachment_count=True,
        )

    def perform_service(self, form):
        delete_entry(self.entry)
