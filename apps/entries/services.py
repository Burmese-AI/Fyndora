from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from guardian.shortcuts import assign_perm

from apps.attachments.services import create_attachments, replace_or_append_attachments
from apps.auditlog.business_logger import BusinessAuditLogger
from apps.core.utils import model_update, percent_change
from apps.currencies.models import Currency
from apps.currencies.selectors import get_closest_exchanged_rate
from apps.organizations.models import Organization, OrganizationExchangeRate
from apps.teams.constants import TeamMemberRole
from apps.teams.models import TeamMember
from apps.workspaces.models import Workspace, WorkspaceExchangeRate, WorkspaceTeam

from .constants import EntryStatus, EntryType
from .models import Entry
from .stats import EntryStats


def _extract_user_from_actor(actor):
    """
    Extract user from actor (TeamMember or OrganizationMember).
    """
    if isinstance(actor, TeamMember):
        return actor.organization_member.user
    elif hasattr(actor, "user"):
        return actor.user
    else:
        return actor

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
        raise ValueError("No exchange rate is defined for the given currency and date.")

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

    # Update Provided Fields
    entry.amount = amount
    entry.currency = currency
    entry.occurred_at = occurred_at
    entry.description = description

    if new_exchange_rate_used:
        entry.exchange_rate_used = new_exchange_rate_used.rate
        entry.org_exchange_rate_ref = (
            new_exchange_rate_used
            if isinstance(new_exchange_rate_used, OrganizationExchangeRate)
            else None
        )
        entry.workspace_exchange_rate_ref = (
            new_exchange_rate_used
            if isinstance(new_exchange_rate_used, WorkspaceExchangeRate)
            else None
        )

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

    # Log entry update with rich context
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
    user = _extract_user_from_actor(last_status_modified_by)

    BusinessAuditLogger.log_status_change(
        user=user,
        entity=entry,
        old_status=old_status,
        new_status=status,
        request=request,
        status_note=status_note,
        modifier_type="org_member"
        if hasattr(last_status_modified_by, "organization")
        else "team_member",
    )


def delete_entry(entry: Entry, user=None, request=None):
    """
    Service to delete an entry.
    """

    if entry.last_status_modified_by:
        raise ValidationError(
            "Cannot delete an entry when someone has already modified the status."
        )

    if entry.status != EntryStatus.PENDING:
        raise ValidationError("Cannot delete an entry that is not pending review")

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


def entry_create(
    *,
    submitted_by,
    entry_type,
    amount,
    description,
    workspace=None,
    workspace_team=None,
    organization=None,
    occurred_at=None,
    currency=None,
):
    """
    Service to create a new entry.
    """

    # Get workspace from workspace_team if workspace is not provided
    workspace = workspace or (workspace_team.workspace if workspace_team else None)

    # Get organization from submitted_by if not provided
    if not organization:
        if isinstance(submitted_by, TeamMember):
            organization = submitted_by.organization_member.organization
        else:
            organization = submitted_by.organization

    # Set default occurred_at to today if not provided
    if not occurred_at:
        occurred_at = date.today()

    # Set default currency to USD if not provided
    if not currency:
        currency, _ = Currency.objects.get_or_create(code="USD", name="US Dollar")

    # Validate workspace requirements based on entry type
    if entry_type == EntryType.WORKSPACE_EXP and not workspace:
        raise ValidationError("Workspace is required for workspace expense entries")

   
    # If submitter is a team member, validate workspace_team for certain entry types
    if (
        isinstance(submitted_by, TeamMember)
        and entry_type
        in [EntryType.INCOME, EntryType.DISBURSEMENT, EntryType.REMITTANCE]
        and not workspace_team
    ):
        raise ValidationError("Workspace team is required for team-based entries")

    # Get the closest exchange rate
    exchange_rate_used = get_closest_exchanged_rate(
        currency=currency,
        occurred_at=occurred_at,
        organization=organization,
        workspace=workspace,
    )
    if not exchange_rate_used:
        raise ValueError("No exchange rate is defined for the given currency and date.")

    # Determine submitter fields
    submitted_by_org_member = None
    submitted_by_team_member = None
    if isinstance(submitted_by, TeamMember):
        submitted_by_team_member = submitted_by
    else:
        submitted_by_org_member = submitted_by

    entry_data = {
        "entry_type": entry_type,
        "amount": amount,
        "description": description,
        "organization": organization,
        "workspace": workspace,
        "workspace_team": workspace_team,
        "occurred_at": occurred_at,
        "currency": currency,
        "exchange_rate_used": exchange_rate_used.rate,
        "org_exchange_rate_ref": exchange_rate_used
        if isinstance(exchange_rate_used, OrganizationExchangeRate)
        else None,
        "workspace_exchange_rate_ref": exchange_rate_used
        if isinstance(exchange_rate_used, WorkspaceExchangeRate)
        else None,
        "submitted_by_org_member": submitted_by_org_member,
        "submitted_by_team_member": submitted_by_team_member,
    }

    entry = Entry()

    with transaction.atomic():
        entry = model_update(entry, entry_data)

        user = (
            submitted_by.organization_member.user
            if isinstance(submitted_by, TeamMember)
            else submitted_by.user
        )

        # Log entry creation with rich business context
        BusinessAuditLogger.log_entry_action(
            user=user,
            entry=entry,
            action="submit",
            entry_amount=str(amount),
            currency_code=currency.code,
            exchange_rate=exchange_rate_used.rate,
            submitter_type="org_member" if submitted_by_org_member else "team_member",
            workspace_required=entry_type == EntryType.WORKSPACE_EXP,
            team_based_entry=entry_type
            in [EntryType.INCOME, EntryType.DISBURSEMENT, EntryType.REMITTANCE],
        )

    return entry


def _validate_review_data(*, status, notes=None):
    """
    Helper function to validate review data.
    """
    if status not in [EntryStatus.APPROVED, EntryStatus.REJECTED]:
        raise ValidationError(f"Invalid review status: {status}")

    # Require notes for reject and flag operations
    if status == EntryStatus.REJECTED and not notes:
        raise ValidationError(f"Notes are required when {status} an entry")


def entry_review(
    *, entry, reviewer, status, is_flagged=False, notes=None, request=None
):
    """
    Service to review an entry (approve, reject, flag).
    """
    # Allow flagging with current status
    if is_flagged:
        if not notes:
            raise ValidationError("Notes are required when flagging an entry.")
    else:
        _validate_review_data(status=status, notes=notes)

    if not (
        entry.status == EntryStatus.PENDING or (is_flagged and entry.status == status)
    ):
        raise ValidationError(f"Cannot review entry with status: {entry.status}")

    entry.status = status
    entry.last_status_modified_by = reviewer
    entry.status_note = notes or ""
    entry.is_flagged = is_flagged
    entry.save(
        update_fields=["status", "last_status_modified_by", "status_note", "is_flagged"]
    )

    # Log review action with rich business context
    user = _extract_user_from_actor(reviewer)

    if is_flagged:
        action = "flag"
    elif status == EntryStatus.APPROVED:
        action = "approve"
    elif status == EntryStatus.REJECTED:
        action = "reject"
    else:
        action = "review"

    BusinessAuditLogger.log_entry_action(
        user=user,
        entry=entry,
        action=action,
        request=request,
        notes=notes,
        reviewer_type="org_member"
        if hasattr(reviewer, "organization")
        else "team_member",
        previous_status=entry.status,
        flagged=is_flagged,
    )

    return entry


def approve_entry(*, entry, reviewer, notes=None, request=None):
    """
    Service to approve an entry.
    """
    return entry_review(
        entry=entry,
        reviewer=reviewer,
        status=EntryStatus.APPROVED,
        notes=notes,
        request=request,
    )


def reject_entry(*, entry, reviewer, notes, request=None):
    """
    Service to reject an entry.
    """
    return entry_review(
        entry=entry,
        reviewer=reviewer,
        status=EntryStatus.REJECTED,
        notes=notes,
        request=request,
    )


def flag_entry(*, entry, reviewer, notes, request=None):
    """
    Service to flag an entry for further review.
    """
    return entry_review(
        entry=entry,
        reviewer=reviewer,
        status=entry.status,
        is_flagged=True,
        notes=notes,
        request=request,
    )


def bulk_review_entries(*, entries, reviewer, status, notes=None, request=None):
    """
    Service to review multiple entries at once.
    """
    _validate_review_data(status=status, notes=notes)

    reviewed_entries = []

    audit_user = _extract_user_from_actor(reviewer)

    with transaction.atomic():
        for entry in entries:
            if entry.status != EntryStatus.PENDING and not entry.is_flagged:
                continue  # Skip entries that can't be reviewed

            entry_data = {
                "status": status,
                "last_status_modified_by": reviewer,
                "status_note": notes or "",
            }

            entry = model_update(entry, entry_data)
            reviewed_entries.append(entry)

        # Log bulk operation with rich context
        if reviewed_entries:
            operation_type = f"bulk_{status.lower()}_entries"
            BusinessAuditLogger.log_bulk_operation(
                user=audit_user,
                operation_type=operation_type,
                affected_objects=reviewed_entries,
                request=request,
                review_status=status,
                review_notes=notes,
                reviewer_type="org_member"
                if hasattr(reviewer, "organization")
                else "team_member",
                total_processed=len(reviewed_entries),
                total_requested=len(entries),
            )

    return reviewed_entries


def entry_update(*, entry, updated_by, request=None, **fields_to_update):
    """
    Service to update an existing entry.
    """

    allowed_fields = ["description", "amount", "workspace", "workspace_team"]
    update_data = {}

    # Filter allowed fields
    for field, value in fields_to_update.items():
        if field in allowed_fields:
            update_data[field] = value

    if not update_data:
        raise ValidationError("No valid fields to update")

    if entry.status == EntryStatus.APPROVED:
        raise ValidationError("Cannot update an approved entry")

    user = (
        updated_by.organization_member.user
        if isinstance(updated_by, TeamMember)
        else updated_by.user
    )

    # Store original values for audit logging
    original_values = {}
    for field in update_data.keys():
        original_values[field] = getattr(entry, field)

    with transaction.atomic():
        entry = model_update(entry, update_data)

        # Log entry update with rich business context
        BusinessAuditLogger.log_entry_action(
            user=user,
            entry=entry,
            action="update",
            request=request,
            updated_fields=list(update_data.keys()),
            original_values=original_values,
            new_values=update_data,
            updater_type="org_member"
            if hasattr(updated_by, "organization")
            else "team_member",
            entry_status=entry.status,
        )

    return entry


def get_org_expense_stats(organization):
    instance = EntryStats(
        entry_types=[EntryType.ORG_EXP],
        organization=organization,
    )
    total = instance.total()
    this_month = instance.this_month()
    last_month = instance.last_month()
    avg_monthly = instance.average_monthly()

    return [
        {
            "title": "Total Expenses",
            "value": total,
            "subtitle": percent_change(total, last_month),
            "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z"/></svg>',
        },
        {
            "title": "This Month's Expenses",
            "value": this_month,
            "subtitle": percent_change(this_month, last_month),
            "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-9-6h.008v.008H12v-.008ZM12 15h.008v.008H12V15Zm0 2.25h.008v.008H12v-.008ZM9.75 15h.008v.008H9.75V15Zm0 2.25h.008v.008H9.75v-.008ZM7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm6.75-4.5h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V15Zm0 2.25h.008v.008h-.008v-.008Zm2.25-4.5h.008v.008H16.5v-.008Zm0 2.25h.008v.008H16.5V15Z"/></svg>',
        },
        {
            "title": "Average Monthly Expense",
            "value": avg_monthly,
            "subtitle": percent_change(this_month, avg_monthly),
            "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"/></svg>',
        },
    ]
