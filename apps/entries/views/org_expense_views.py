from typing import Any

from django.db.models.query import QuerySet
from django.http.response import HttpResponse as HttpResponse
from django.urls import reverse
from django.utils import timezone

from apps.core.utils import permission_denied_view
from apps.core.views.base_views import BaseGetModalFormView, BaseGetModalView
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
    BaseEntryBulkActionView,
)
from .mixins import EntryFormMixin, EntryRequiredMixin, StatusFilteringMixin


class OrganizationExpenseListView(
    OrganizationRequiredMixin,
    OrganizationLevelEntryView,
    StatusFilteringMixin,
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
            statuses=[self.request.GET.get("status")]
            if self.request.GET.get("status")
            else [EntryStatus.PENDING],
            search=self.request.GET.get("search"),
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["permissions"] = {
            "can_add_org_expense": can_add_org_expense(
                self.request.user, self.organization
            ),
        }

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
            statuses=[self.request.GET.get("status")]
            if self.request.GET.get("status")
            else [EntryStatus.PENDING],
            search=self.request.GET.get("search"),
        )

    def get_modal_title(self) -> str:
        return "Organization Expense"

    def get_post_url(self) -> str:
        return reverse(
            "organization_expense_create",
            kwargs={"organization_id": self.organization.pk},
        )

    def perform_service(self, form):
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
            statuses=[self.request.GET.get("status")]
            if self.request.GET.get("status")
            else [EntryStatus.PENDING],
            search=self.request.GET.get("search"),
        )

    def perform_service(self, form):
        delete_entry(entry=self.entry, user=self.request.user, request=self.request)


class OrganizationExpenseBulkDeleteView(
    OrganizationRequiredMixin,
    OrganizationLevelEntryView,
    BaseGetModalView,
    StatusFilteringMixin,
    BaseEntryBulkActionView,
):
    table_template_name = "entries/partials/table.html"
    modal_template_name = "components/delete_confirmation_modal.html"

    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            entry_types=[EntryType.ORG_EXP],  
            annotate_attachment_count=True,
            statuses=[EntryStatus.PENDING]          
        )

    def perform_action(self, request, entries):
        valid_ids = [entry.pk for entry in entries if self.validate_entry(entry)]
        if not valid_ids:
            return False, "No valid entries to delete"

        qs_valid = entries.filter(pk__in=valid_ids)
        # Get the count *before* performing the delete operation
        deleted_count = qs_valid.count()
        qs_valid.delete()
        return True, f"Deleted {deleted_count} entry/entries"

    def validate_entry(self, entry):
        # True if
        # 1. Entry status pending
        # 2. Entry status hasn't been modified once
        if (
            entry.status == EntryStatus.PENDING
            and not entry.status_last_updated_at
            and not entry.last_status_modified_by
        ):
            return True
        return False

    def get_post_url(self) -> str:
        return reverse(
            "organization_expense_bulk_delete",
            kwargs={"organization_id": self.organization.pk},
        )

    def get_modal_title(self) -> str:
        return ""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        selected_ids = self.request.GET.getlist("entries")
        context["selected_entry_ids"] = selected_ids
        context["entry_count"] = len(selected_ids)
        if self.request.htmx:
            context["filter_status_value"] = None
            context["filter_search_value"] = None
        return context


class OrganizationExpenseBulkUpdateView(
    OrganizationRequiredMixin,
    OrganizationLevelEntryView,
    BaseGetModalView,
    StatusFilteringMixin,
    BaseEntryBulkActionView,
):
    table_template_name = "entries/partials/table.html"
    modal_template_name = "entries/components/bulk_update_modal.html"

    def get_queryset(self):            
        return get_entries(
            organization=self.organization,
            entry_types=[EntryType.ORG_EXP],
        )
        
    def get_response_queryset(self):
        return get_entries(
            organization=self.organization,
            entry_types=[EntryType.ORG_EXP],
            annotate_attachment_count=True,
            statuses=[EntryStatus.PENDING]
        )
        
    def perform_action(self, request, entries):
        status = request.POST.get("status")
        status_note = request.POST.get("status_note")
        valid_entries = []
        
        for entry in entries:
            if self.validate_entry(entry):
                entry.status = status
                entry.last_status_modified_by = self.org_member
                entry.status_note = status_note
                entry.status_last_updated_at = timezone.now()
                valid_entries.append(entry)        
        if not valid_entries:
            return False, "No valid entries"
        Entry.objects.bulk_update(valid_entries, ["status", "status_note", "last_status_modified_by", "status_last_updated_at"])
        return True, f"Updated {len(valid_entries)} entries"

    def validate_entry(self, entry):
        return True

    def get_post_url(self) -> str:
        return reverse(
            "organization_expense_bulk_update",
            kwargs={"organization_id": self.organization.pk},
        )

    def get_modal_title(self) -> str:
        return ""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        selected_ids = self.request.GET.getlist("entries")
        context["selected_entry_ids"] = selected_ids
        context["entry_count"] = len(selected_ids)
        context["modal_status_options"] = EntryStatus.choices
        if self.request.htmx:
            context["filter_status_value"] = None
            context["filter_search_value"] = None
            
        return context
