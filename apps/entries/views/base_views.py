import json

from django.http import HttpResponse
from django.contrib import messages
from django.views.generic import TemplateView
from django.template.loader import render_to_string

from ..models import Entry
from ..constants import CONTEXT_OBJECT_NAME, DETAIL_CONTEXT_OBJECT_NAME
from .mixins import (
    EntryRequiredMixin,
    EntryUrlIdentifierMixin,
)
from apps.entries.constants import EntryType
from apps.core.views.crud_base_views import BaseDetailView
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
    HtmxOobResponseMixin,
    HtmxInvalidResponseMixin,
)


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


# views/bulk_actions.py


class BaseEntryBulkActionView(
    HtmxInvalidResponseMixin, HtmxOobResponseMixin, TemplateView
):
    table_template_name = None
    context_object_name = CONTEXT_OBJECT_NAME

    def get_queryset(self):
        """
        Override this to return the correct filtered queryset.
        Example: Entry.objects.filter(organization=self.org, workspace=self.ws)
        """
        raise NotImplementedError("Subclasses must implement get_base_queryset()")

    def perform_action(self, entries, user):
        """
        Perform the actual action (update/delete).
        Must be implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement perform_action()")

    def validate_entry(self, entry: Entry, user) -> bool:
        """
        Optional per-entry validation (e.g., status checks).
        Can be overridden.
        """
        return True

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

            # List existing entry ids
            existing_ids = set(entries.values_list("pk", flat=True))

            # List missing or inaccessible entries
            requested_set = set(entry_ids)
            missing_ids = requested_set - existing_ids

            # Validate each entry
            valid_entries = []
            for entry in entries:
                if self.validate_entry(entry, request.user):
                    valid_entries.append(entry)

            # After validation
            valid_ids = [entry.pk for entry in valid_entries]
            if not valid_ids:
                raise Exception("No valid entries")

            qs_valid_entries = base_qs.filter(pk__in=valid_ids)

            self.perform_action(qs_valid_entries, request.user)

            messages.success(
                self.request,
                f"Performed the bulk action on {qs_valid_entries.count()} entries successfully",
            )

            return self._render_htmx_success_response()

        except Exception as e:
            messages.error(self.request, str(e))
            return self._render_htmx_error_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        from apps.core.utils import get_paginated_context

        queryset = self.get_queryset()
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
