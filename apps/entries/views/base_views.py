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
from apps.entries.selectors import get_entries
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


class BaseEntryBulkActionView(
    HtmxInvalidResponseMixin, HtmxOobResponseMixin, TemplateView
):
    table_template_name = None
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

    def perform_action(self, request, entries) -> tuple[bool, str | None]:
        """
        Perform the actual action (update/delete).
        """
        return True, None

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
