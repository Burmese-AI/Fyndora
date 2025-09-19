from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.attachments.services import create_attachments, replace_or_append_attachments
from apps.auditlog.business_logger import BusinessAuditLogger
from apps.core.utils import handle_service_errors
from apps.currencies.models import Currency
from apps.currencies.selectors import get_closest_exchanged_rate, get_currency_by_code
from apps.entries.exceptions import EntryServiceError
from apps.organizations.models import Organization, OrganizationExchangeRate
from apps.workspaces.models import Workspace, WorkspaceExchangeRate, WorkspaceTeam

from .constants import EntryStatus, EntryType
from .models import Entry


class EntryService:
    @staticmethod
    def build_entry(
        *,
        currency_code,
        amount,
        occurred_at,
        description,
        entry_type: EntryType,
        organization: Organization,
        workspace: Workspace = None,
        workspace_team: WorkspaceTeam = None,
        submitted_by_org_member=None,
        submitted_by_team_member=None,
        status: EntryStatus = EntryStatus.PENDING,
        status_note="",
        status_last_modified_at=timezone.now(),
    ):
        # Get Currency by code
        currency = get_currency_by_code(currency_code)
        if not currency:
            return None
        # Get the closest exchange rate
        exchange_rate_used = get_closest_exchanged_rate(
            currency=currency,
            occurred_at=occurred_at,
            organization=organization,
            workspace=workspace,
        )
        if not exchange_rate_used:
            return None
        # Prepare entry object
        entry = Entry(
            entry_type=entry_type,
            organization=organization,
            workspace=workspace,
            workspace_team=workspace_team,
            description=description,
            amount=amount,
            occurred_at=occurred_at,
            currency=currency,
            exchange_rate_used=exchange_rate_used.rate,
            org_exchange_rate_ref=exchange_rate_used
            if isinstance(exchange_rate_used, OrganizationExchangeRate)
            else None,
            workspace_exchange_rate_ref=exchange_rate_used
            if isinstance(exchange_rate_used, WorkspaceExchangeRate)
            else None,
            submitted_by_org_member=submitted_by_org_member,
            submitted_by_team_member=submitted_by_team_member,
            status=status,
            is_flagged=True,
        )
        # Add status related metadata if not pending
        if status != EntryStatus.PENDING:
            entry.status_note = status_note
            entry.status_last_updated_at = status_last_modified_at
            entry.last_status_modified_by = submitted_by_org_member

        return entry

    @staticmethod
    @handle_service_errors(EntryServiceError)
    def bulk_create_entry(*, entries: list[Entry]):
        return Entry.objects.bulk_create(entries)

    @staticmethod
    @handle_service_errors(EntryServiceError)
    def create_entry_with_attachments(
        *,
        amount,
        occurred_at,
        description,
        attachments,
        entry_type: EntryType,
        organization: Organization,
        workspace: Workspace = None,
        workspace_team: WorkspaceTeam = None,
        currency,
        submitted_by_org_member=None,
        submitted_by_team_member=None,
        user=None,
        request=None,
    ) -> Entry:
        """
        Service to create a new entry with attachments.
        """

        is_attachment_provided = True if attachments else False

        # Get the closest exchange rate
        exchange_rate_used = get_closest_exchanged_rate(
            currency=currency,
            occurred_at=occurred_at if occurred_at else date.today(),
            organization=organization,
            workspace=workspace,
        )
        if not exchange_rate_used:
            raise ValueError(
                "No exchange rate is defined for the given currency and date."
            )

        # Potential Error
        # NOTE: if currency is soft-deleted, currency obj can't be obtained
        # unless its similar object has been created

        with transaction.atomic():
            # Create the Entry
            entry = Entry.objects.create(
                entry_type=entry_type,
                amount=amount,
                occurred_at=occurred_at,
                description=description,
                organization=organization,
                workspace=workspace
                or (workspace_team.workspace if workspace_team else None),
                workspace_team=workspace_team,
                currency=currency,
                exchange_rate_used=exchange_rate_used.rate,
                org_exchange_rate_ref=exchange_rate_used
                if isinstance(exchange_rate_used, OrganizationExchangeRate)
                else None,
                workspace_exchange_rate_ref=exchange_rate_used
                if isinstance(exchange_rate_used, WorkspaceExchangeRate)
                else None,
                submitted_by_org_member=submitted_by_org_member,
                submitted_by_team_member=submitted_by_team_member,
                is_flagged=not is_attachment_provided,
            )

            # Create the Attachments if any were provided
            if is_attachment_provided:
                create_attachments(
                    entry=entry,
                    attachments=attachments,
                    user=user,
                    request=request,
                )

            # Log entry creation with rich context
            if user:
                BusinessAuditLogger.log_entry_action(
                    user=user,
                    entry=entry,
                    action="submit",
                    request=request,
                    entry_amount=str(amount),
                    currency_code=currency.code,
                    exchange_rate=exchange_rate_used.rate,
                    has_attachments=is_attachment_provided,
                    attachment_count=len(attachments) if attachments else 0,
                    submitter_type="org_member"
                    if submitted_by_org_member
                    else "team_member",
                )

        return entry

    @staticmethod
    @handle_service_errors(EntryServiceError)
    def update_entry_user_inputs(
        *,
        entry: Entry,
        organization: Organization,
        workspace: Workspace = None,
        amount,
        occurred_at,
        description,
        currency: Currency,
        attachments,
        replace_attachments: bool,
        user=None,
        request=None,
    ):
        if entry.status != EntryStatus.PENDING:
            raise ValidationError(
                "User can only update Entry info during the pending stage."
            )

        # Check if currency or occurred_at values are changed or not
        is_currency_changed = entry.currency.code != currency.code
        is_occurred_at_changed = entry.occurred_at != occurred_at
        # If changed, update exchange_rate_used, org_exchange_rate_ref, workspace_exchange_rate_ref
        new_exchange_rate_used = None
        if is_currency_changed or is_occurred_at_changed:
            new_exchange_rate_used = get_closest_exchanged_rate(
                currency=currency,
                occurred_at=occurred_at,
                organization=organization,
                workspace=workspace,
            )
            if not new_exchange_rate_used:
                raise ValueError(
                    "No exchange rate is defined for the given currency and date."
                )

        with transaction.atomic():
            # Update Provided Fields
            entry.amount = amount
            entry.currency = currency
            entry.occurred_at = occurred_at
            entry.description = description

            if new_exchange_rate_used:
                entry.exchange_rate_used = new_exchange_rate_used.rate
                # Reset org_exchange_rate_ref
                entry.org_exchange_rate_ref = (
                    new_exchange_rate_used
                    if isinstance(new_exchange_rate_used, OrganizationExchangeRate)
                    else None
                )
                # Reset workspace_exchange_rate_ref
                entry.workspace_exchange_rate_ref = (
                    new_exchange_rate_used
                    if isinstance(new_exchange_rate_used, WorkspaceExchangeRate)
                    else None
                )

                
            # Set audit context to prevent duplicate logging from signal handlers
            if user:
                entry._audit_user = user
            entry.save()

            # If new attachments were provided, replace existing ones or append the new ones
            if attachments:
                replace_or_append_attachments(
                    entry=entry,
                    attachments=attachments,
                    replace_attachments=replace_attachments,
                    user=user,
                    request=request,
                )

                # If the entry was flagged, unflag it
                if entry.is_flagged:
                    entry.is_flagged = False
                    entry.save(update_fields=["is_flagged"])


            # Business logic logging: Log entry submission with rich context
            if user:
                BusinessAuditLogger.log_entry_action(
                    user=user,
                    entry=entry,
                    action="update",
                    request=request,
                    updated_fields=["amount", "currency", "occurred_at", "description"],
                    currency_changed=is_currency_changed,
                    occurred_at_changed=is_occurred_at_changed,
                    exchange_rate_updated=new_exchange_rate_used is not None,
                    attachments_updated=bool(attachments),
                    replace_attachments=replace_attachments if attachments else False,
                    was_flagged=entry.is_flagged,
                )

    @staticmethod
    @handle_service_errors(EntryServiceError)
    def update_entry_status(
        *, entry: Entry, status, status_note, last_status_modified_by, request=None
    ):
        old_status = entry.status
        entry.status = status
        entry.status_note = status_note
        entry.last_status_modified_by = last_status_modified_by
        entry.status_last_updated_at = timezone.now()
        entry.save()

        # Log status change with rich context
        BusinessAuditLogger.log_status_change(
            user=entry.last_modifier,
            entity=entry,
            old_status=old_status,
            new_status=status,
            request=request,
            status_note=status_note,
            modifier_type="org_member"
            if hasattr(last_status_modified_by, "organization")
            else "team_member",
        )

    @staticmethod
    @handle_service_errors(EntryServiceError)
    def bulk_update_entry_status(*, entries: list[Entry], request=None):
        Entry.objects.bulk_update(
            entries,
            [
                "status",
                "status_note",
                "last_status_modified_by",
                "status_last_updated_at",
            ],
        )
        return entries

    @staticmethod
    @handle_service_errors(EntryServiceError)
    def delete_entry(*, entry: Entry, user=None, request=None):
        """
        Service to delete an entry.
        """
        if entry.last_status_modified_by:
            raise EntryServiceError(
                "Cannot delete an entry when someone has already modified the status."
            )

        if entry.status != EntryStatus.PENDING:
            raise EntryServiceError("Cannot delete an entry that is not pending review")

        # Log entry deletion before deleting
        if user:
            BusinessAuditLogger.log_entry_action(
                user=user,
                entry=entry,
                action="delete",
                request=request,
                entry_amount=str(entry.amount),
                entry_status=entry.status,
                had_attachments=entry.attachments.exists(),
                deletion_reason="user_initiated",
            )

        entry.delete()
        return entry

    @staticmethod
    @handle_service_errors(EntryServiceError)
    def bulk_delete_entries(*, entries: list[Entry], user=None, request=None):
        entries.delete()
        return entries
