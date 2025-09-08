import json
from typing import Any
import traceback
import csv
import io

from django.db.models import QuerySet
from django.http import HttpResponse
from django.contrib import messages
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction

from apps.currencies.selectors import get_closest_exchanged_rate, get_currency_by_code
from apps.entries.forms import BaseImportEntryForm
from apps.organizations.models import OrganizationExchangeRate
from apps.workspaces.models import WorkspaceExchangeRate, WorkspaceTeam

from ..models import Entry
from ..constants import CONTEXT_OBJECT_NAME, DETAIL_CONTEXT_OBJECT_NAME, EntryStatus
from .mixins import (
    EntryFormMixin,
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
from apps.entries.services import bulk_delete_entries, bulk_update_entry_status
from apps.remittance.services import (
    calculate_due_amount,
    calculate_paid_amount,
    update_remittance,
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
    HtmxInvalidResponseMixin, 
    HtmxOobResponseMixin, 
    TemplateView
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

    def perform_post_action(self, entries: QuerySet[Entry]):
        """Optional Post Action"""
        pass


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
            bulk_delete_entries(
                entries=valid_entries,
                user=self.request.user,
                request=self.request,
            )

            # Note: Since only unmodified entries with Pending status are allowed to be deleted,
            # Post action might not be required (will be invalid)
            if not is_expense_entry and affected_workspace_teams:
                self.perform_post_action(affected_workspace_teams)

        return True, f"Deleted {deleted_count} entry/entries"

    def perform_post_action(self, workspace_teams: set[WorkspaceTeam]):
        for team in workspace_teams:
            remittance = team.remittance
            # After delete, both due/paid amounts might change
            remittance.due_amount = calculate_due_amount(workspace_team=team)
            remittance.paid_amount = calculate_paid_amount(workspace_team=team)
            update_remittance(remittance=remittance)


class BaseEntryBulkUpdateView(BaseEntryBulkActionView):
    modal_template_name = "entries/components/bulk_update_modal.html"

    def perform_action(self, request, entries):
        self.new_status = request.POST.get("status")
        self.status_note = request.POST.get("status_note")
        valid_entries = []
        is_expense_entry = False

        # Filter out entries whose statuses are the same as the new one
        entries = entries.exclude(status=self.new_status)
        with transaction.atomic():
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
            # Return False for no valid entries
            if not valid_entries:
                return False, "No valid entries"
            # Bulk Update
            bulk_update_entry_status(entries=valid_entries, request=request)
            # If no expense entry is included, perform post action to update remittance
            if not is_expense_entry:
                self.perform_post_action(
                    entries=valid_entries, new_status=self.new_status
                )
        return True, f"Updated {len(valid_entries)} entries"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["modal_status_options"] = EntryStatus.choices
        return context

    def perform_post_action(self, entries: QuerySet[Entry], new_status):
        entries_by_team = {}
        # Group Entries by Workspace Team ID
        for entry in entries:
            workspace_team_id = entry.workspace_team.pk
            if workspace_team_id not in entries_by_team:
                entries_by_team[workspace_team_id] = {
                    "entries": [],
                    "is_due_amount_update_required": True,  # Note: Updating to/from Approved status can affect due amount
                    "is_paid_amount_update_required": False,
                }
            entries_by_team[workspace_team_id]["entries"].append(entry)
            # Check entry type if paid amount update is required
            if (
                not entries_by_team[workspace_team_id]["is_paid_amount_update_required"]
                and entry.entry_type == EntryType.REMITTANCE
            ):
                entries_by_team[workspace_team_id]["is_paid_amount_update_required"] = (
                    True
                )

        for workspace_team_id, dict_val in entries_by_team.items():
            workspace_team = dict_val["entries"][0].workspace_team
            remittance = workspace_team.remittance
            if dict_val["is_due_amount_update_required"]:
                remittance.due_amount = calculate_due_amount(
                    workspace_team=workspace_team
                )
            if dict_val["is_paid_amount_update_required"]:
                remittance.paid_amount = calculate_paid_amount(
                    workspace_team=workspace_team
                )
            update_remittance(remittance=remittance)


class BaseEntryBulkCreateView(BaseEntryBulkActionView):
    modal_template_name = "entries/components/bulk_create_modal.html"
    
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
        print(kwargs)
        return kwargs

    
    def post(self, request, *args, **kwargs):
        try:
            print(f">>> POST: {request.POST}")
            print(f">>> FILES: {request.FILES}")

            # Collect kwargs from parent method
            form_kwargs = self.get_form_kwargs()
            form_kwargs.update({
                "data": request.POST,
                "files": request.FILES,
            })

            # Bind form with both request data and extra kwargs
            self.form = self.form_class(**form_kwargs)

            if not self.form.is_valid():
                messages.error(self.request, "Invalid Form Submission")
                return self._render_htmx_error_response(form=self.form)
            
            #Extract valid values from form
            status = self.form.cleaned_data['status']
            backup_description = self.form.cleaned_data['backup_description']
            #Add it to the list of valid ones
            #Open CSV 
            uploaded_file = request.FILES["file"]
            data = io.TextIOWrapper(uploaded_file.file, encoding="utf-8")
            reader = csv.DictReader(data)
            valid_entries = []
            #Values
            organization = getattr(self, "organization", None)
            workspace = getattr(self, "workspace", None)
            workspace_team = getattr(self, "workspace_team", None)
            #Iterate
            for row in reader:
                # {'Description': 'Taxi', 'Amount': '836.84', 'Occurred At': '2025-08-19', 'Currency': 'USD'}
                print(row)
                description = row["Description"]
                amount = row["Amount"]
                currency = row["Currency"]
                occurred_at = row["Occurred At"]
                #Validate Amount
                #Get closest exchange rate on each row based on the occurred at
                currency = get_currency_by_code(code=currency)
                print(f"Currency => {currency}")
                exchange_rate_used = get_closest_exchanged_rate(
                    currency=currency,
                    occurred_at=occurred_at,
                    organization=organization,
                    workspace=workspace
                )
                print(f"exchange rate => {exchange_rate_used}")
                #If not found, skip
                if not exchange_rate_used:
                    print("Skipped")
                    continue
                #If found, prepare data (exchange rate, its source, status, submitter, backup description)
                entry = Entry(
                    entry_type=EntryType.ORG_EXP,
                    description=description or backup_description,
                    amount=amount,
                    occurred_at=occurred_at,
                    currency=currency,
                    exchange_rate_used=exchange_rate_used.rate,
                    org_exchange_rate_ref=exchange_rate_used if isinstance(exchange_rate_used, OrganizationExchangeRate) else None,
                    workspace_exchange_rate_ref=exchange_rate_used if isinstance(exchange_rate_used, WorkspaceExchangeRate) else None,
                    submitted_by_org_member=self.org_member,
                    submitted_by_team_member=getattr(self, "workspace_team_member", None),
                    status=status,
                    status_last_updated_at=timezone.now(),
                    last_status_modified_by=self.org_member,
                    status_note="",
                    is_flagged=True,
                    organization=organization,
                    workspace=workspace,
                    workspace_team=workspace_team,
                )
                valid_entries.append(entry)
                print(entry, "\n")
            
            print(len(valid_entries))
            messages.success(self.request, "Success")
            return self._render_htmx_success_response()

        except Exception as e:
            traceback.print_exc()
            messages.error(self.request, str(e))
            return self._render_htmx_error_response(form=self.form)

