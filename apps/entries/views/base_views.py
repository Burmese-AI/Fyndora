import json
from typing import Any

from django.db.models import QuerySet
from django.http import HttpResponse
from django.contrib import messages
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.utils import timezone

from ..models import Entry
from ..constants import CONTEXT_OBJECT_NAME, DETAIL_CONTEXT_OBJECT_NAME, EntryStatus
from .mixins import (
    EntryRequiredMixin,
    EntryUrlIdentifierMixin,
)
from apps.entries.selectors import get_entries
from apps.entries.constants import EntryType
from apps.core.views.crud_base_views import BaseDetailView
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
    HtmxOobResponseMixin,
    HtmxInvalidResponseMixin,
)
from apps.entries.services import bulk_delete_entries, bulk_update_entry_status

class OrganizationLevelEntryView(EntryUrlIdentifierMixin):
    def get_entry_type(self):
        return EntryType.ORG_EXP


class WorkspaceLevelEntryView(EntryUrlIdentifierMixin):
    def get_entry_type(self):
        return EntryType.WORKSPACE_EXP


class TeamLevelEntryView(EntryUrlIdentifierMixin):
    def get_entry_type(self):
        return EntryType.INCOME


class EntryDetailView(OrganizationRequiredMixin, EntryRequiredMixin, BaseDetailView):
    model = Entry
    template_name = "entries/components/detail_modal.html"
    context_object_name = DETAIL_CONTEXT_OBJECT_NAME

    def get_queryset(self):
        return Entry.objects.filter(organization=self.organization)


class BaseEntryBulkActionView(
    HtmxInvalidResponseMixin, HtmxOobResponseMixin, TemplateView
):
    table_template_name = "entries/partials/table.html"
    context_object_name = CONTEXT_OBJECT_NAME

    def get_queryset(self):
        """
        Override this to return the correct filtered queryset.
        """
        raise NotImplementedError("Subclasses must implement get_base_queryset()")
    
    def get_response_queryset(self):
        """
        Override this to return the correct queryset for the response.
        """
        return self.get_queryset()

    def perform_action(self, request, entries: QuerySet[Entry]) -> tuple[bool, str | None]:
        """
        Perform the actual action (update/delete).
        """
        return True, None
    
    def validate_entry(self, entry: Entry) -> bool:
        """Per-entry validation"""
        return True
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        selected_ids = self.request.GET.getlist("entries")
        context["selected_entry_ids"] = selected_ids
        context["entry_count"] = len(selected_ids)
        if self.request.htmx:
            context["filter_status_value"] = None
            context["filter_search_value"] = None
            context["filter_type_value"] = None
            context["filter_team_value"] = None
        return context

    def parse_entry_ids(self, request):
        """Parse entry IDs from request (form or JSON)"""
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                return data.get("entries", [])
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON")
        else:
            return request.POST.getlist("entries")

    def post(self, request, *args, **kwargs):
        try:
            # Parse IDs
            entry_ids = self.parse_entry_ids(request)

            if not entry_ids:
                raise Exception("No entries selected")

            # Get base queryset
            base_qs = self.get_queryset()
            
            # Filter out the entries
            entries = base_qs.filter(pk__in=entry_ids)
            
            # Validate each entry
            success, message = self.perform_action(request, entries)
            
            if not success:
                messages.error(self.request, message)
                return self._render_htmx_error_response()
            
            messages.success(self.request, message)
            return self._render_htmx_success_response()

        except Exception as e:
            messages.error(self.request, str(e))
            return self._render_htmx_error_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        from apps.core.utils import get_paginated_context

        queryset = self.get_response_queryset()
        table_context = get_paginated_context(
            queryset=queryset,
            context=base_context,
            object_name=self.context_object_name,
        )

        table_html = render_to_string(
            self.table_template_name, context=table_context, request=self.request
        )
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        response = HttpResponse(f"{message_html}{table_html}")
        response["HX-trigger"] = "success"
        return response

class BaseEntryBulkDeleteView(BaseEntryBulkActionView):
    modal_template_name = "components/delete_confirmation_modal.html"

    def perform_action(self, request, entries):
        valid_ids = [entry.pk for entry in entries if self.validate_entry(entry)]
        if not valid_ids:
            print(f"No valid id => {valid_ids}")
            return False, "No valid entries to delete"

        qs_valid = entries.filter(pk__in=valid_ids)
        deleted_count = qs_valid.count()
        bulk_delete_entries(
            entries=qs_valid,
            user=self.request.user,
            request=self.request,
        )
        return True, f"Deleted {deleted_count} entry/entries"
    
class BaseEntryBulkUpdateView(BaseEntryBulkActionView):
    modal_template_name = "entries/components/bulk_update_modal.html"

    def perform_action(self, request, entries):
        self.new_status = request.POST.get("status")
        self.status_note = request.POST.get("status_note")
        valid_entries = []
        
        #Filter out entries whose statuses are the same as the new one
        entries = entries.exclude(status=self.new_status)

        for entry in entries:
            if self.validate_entry(entry):
                entry.status = self.new_status
                entry.last_status_modified_by = self.org_member
                entry.status_note = self.status_note
                entry.status_last_updated_at = timezone.now()
                valid_entries.append(entry)

        if not valid_entries:
            return False, "No valid entries"
        bulk_update_entry_status(entries=valid_entries, request=request)
        return True, f"Updated {len(valid_entries)} entries"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["modal_status_options"] = EntryStatus.choices
        return context

