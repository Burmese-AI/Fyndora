import json
from typing import Any
import traceback

from django.db.models import QuerySet
from django.http import HttpResponse
from django.contrib import messages
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction

from apps.entries.validators import EntryCSVValidator
from apps.workspaces.models import WorkspaceTeam

from ..models import Entry
from ..constants import CONTEXT_OBJECT_NAME, DETAIL_CONTEXT_OBJECT_NAME, EntryStatus
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
from apps.entries.services import (
    EntryService,
)
from apps.remittance.services import (
    RemittanceService,
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
    table_template_name = "entries/layouts/base_entry_content_layout.html"
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

    def perform_action(
        self, request, entries: QuerySet[Entry]
    ) -> tuple[bool, str | None]:
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

    def perform_post_action(self, *args, **kwargs):
        """
        Perform post action after the bulk action is performed.
        """
        pass

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
            traceback.print_exc()
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
        is_expense_entry = False
        valid_entries = []
        affected_workspace_teams: set[WorkspaceTeam] = set()

        for entry in entries:
            if self.validate_entry(entry):
                valid_entries.append(entry)
                affected_workspace_teams.add(entry.workspace_team)

            # Check if entries are of Org/Workspace Expense
            if not is_expense_entry and entry.entry_type in [
                EntryType.ORG_EXP,
                EntryType.WORKSPACE_EXP,
            ]:
                is_expense_entry = True

        if not valid_entries:
            return False, "No valid entries to delete"

        deleted_count = len(valid_entries)
        with transaction.atomic():
            # Convert list into queryset
            valid_entries = entries.filter(pk__in=[entry.pk for entry in valid_entries])
            EntryService.bulk_delete_entries(
                entries=valid_entries,
                user=self.request.user,
                request=self.request,
            )

            # Note: Since only unmodified entries with Pending status are allowed to be deleted,
            # Post action might not be required (will be invalid)
            if not is_expense_entry and affected_workspace_teams:
                RemittanceService.bulk_sync_remittance(
                    workspace_teams=list(affected_workspace_teams)
                )

        return True, f"Deleted {deleted_count} entry/entries"


class BaseEntryBulkUpdateView(BaseEntryBulkActionView):
    modal_template_name = "entries/components/bulk_update_modal.html"

    def perform_action(self, request, entries):
        self.new_status = request.POST.get("status")
        self.status_note = request.POST.get("status_note")
        valid_entries = []
        affected_workspace_teams: set[WorkspaceTeam] = set()
        is_expense_entry = False

        # Filter out entries whose statuses are the same as the new one
        entries = entries.exclude(status=self.new_status)
        with transaction.atomic():
            # Iterate via entries to validate and update status
            for entry in entries:
                # Check if entries are of Org/Workspace Expense
                if not is_expense_entry and entry.entry_type in [
                    EntryType.ORG_EXP,
                    EntryType.WORKSPACE_EXP,
                ]:
                    # Set True to confirm for running post action method
                    is_expense_entry = True

                # Append the entry to the list if valid along with new values
                if self.validate_entry(entry):
                    entry.status = self.new_status
                    entry.last_status_modified_by = self.org_member
                    entry.status_note = self.status_note
                    entry.status_last_updated_at = timezone.now()
                    valid_entries.append(entry)
                    affected_workspace_teams.add(entry.workspace_team)

            # Return False for no valid entries
            if not valid_entries:
                return False, "No valid entries"

            # Bulk Update
            EntryService.bulk_update_entry_status(
                entries=valid_entries, request=request
            )

            # If no expense entry is included, prepare to sync remittance
            if not is_expense_entry:
                RemittanceService.bulk_sync_remittance(
                    workspace_teams=list(affected_workspace_teams)
                )

        return True, f"Updated {len(valid_entries)} entries"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["modal_status_options"] = EntryStatus.choices
        return context


class BaseEntryBulkCreateView(BaseEntryBulkActionView):
    modal_template_name = "entries/components/bulk_create_modal.html"
    # specify entry type if entry type is not specified in the file
    entry_type_to_create = None

    def get_form_kwargs(self) -> dict:
        kwargs = {}
        kwargs["org_member"] = self.org_member
        kwargs["organization"] = self.organization
        kwargs["is_org_admin"] = self.is_org_admin
        kwargs["is_workspace_admin"] = (
            self.is_workspace_admin if hasattr(self, "is_workspace_admin") else None
        )
        kwargs["is_operation_reviewer"] = (
            self.is_operation_reviewer
            if hasattr(self, "is_operation_reviewer")
            else None
        )
        kwargs["is_team_coordinator"] = (
            self.is_team_coordinator if hasattr(self, "is_team_coordinator") else None
        )
        kwargs["workspace"] = self.workspace if hasattr(self, "workspace") else None
        kwargs["workspace_team"] = (
            self.workspace_team if hasattr(self, "workspace_team") else None
        )
        kwargs["workspace_team_member"] = (
            self.workspace_team_member
            if hasattr(self, "workspace_team_member")
            else None
        )
        kwargs["workspace_team_role"] = (
            self.workspace_team_role if hasattr(self, "workspace_team_role") else None
        )
        return kwargs

    def post(self, request, *args, **kwargs):
        try:
            self.form = self.form_class(
                data=request.POST, files=request.FILES, **self.get_form_kwargs()
            )
            if not self.form.is_valid():
                return self._render_htmx_error_response(form=self.form)

            validator = EntryCSVValidator(request.FILES["file"])
            valid_rows, errors = validator.validate(
                verify_team_level_type=False if self.entry_type_to_create else True
            )

            valid_entries = []
            for row in valid_rows:
                entry = EntryService.build_entry(
                    currency_code=row["Currency"],
                    amount=row["Amount"],
                    occurred_at=row["Occurred At"],
                    description=row["Description"].strip()
                    or self.form.cleaned_data.get("description").strip(),
                    entry_type=self.entry_type_to_create or row["Type"],
                    organization=self.organization,
                    workspace=getattr(self, "workspace", None),
                    workspace_team=getattr(self, "workspace_team", None),
                    submitted_by_org_member=self.org_member,
                    submitted_by_team_member=getattr(
                        self, "workspace_team_member", None
                    ),
                    status=self.form.cleaned_data.get("status"),
                    status_note=self.form.cleaned_data.get("status_note").strip(),
                )
                if entry:
                    valid_entries.append(entry)

            # Validate each entry
            success, message = self.perform_action(request, valid_entries)

            if not success:
                messages.error(self.request, message)
                return self._render_htmx_error_response(form=self.form)

            messages.success(request, f"{message}")
            return self._render_htmx_success_response()

        except Exception as e:
            traceback.print_exc()
            messages.error(request, str(e))
            return self._render_htmx_error_response(form=self.form)

    def perform_action(self, request, entries: list[Entry]) -> tuple[bool, str | None]:
        try:
            if not entries:
                return False, "No valid entry found"

            with transaction.atomic():
                EntryService.bulk_create_entry(entries=entries)
                self.perform_post_action(entries=entries)

            return True, f"Successfully imported {len(entries)} entry/ies"

        except Exception as e:
            return False, f"An Error occurred during bulk create: {e}"
