from guardian.shortcuts import assign_perm
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.auditlog.constants import AuditActionType
from apps.auditlog.services import audit_create
from apps.core.utils import model_update, percent_change
from apps.currencies.models import Currency
from apps.organizations.models import Organization, OrganizationExchangeRate
from apps.teams.models import TeamMember
from apps.attachments.services import replace_or_append_attachments, create_attachments
from apps.teams.constants import TeamMemberRole
from apps.workspaces.models import Workspace, WorkspaceExchangeRate, WorkspaceTeam

from .constants import EntryStatus, EntryType
from .models import Entry
from .permissions import EntryPermissions
from .stats import EntryStats
from datetime import date
from apps.currencies.selectors import get_currency_by_code
from .selectors import get_closest_exchanged_rate


def _check_entry_permissions(*, actor, permission_to_check, entry=None, workspace=None):
    """
    A helper function to centralize permission checking for entry services.
    """
    user = (
        actor.organization_member.user if isinstance(actor, TeamMember) else actor.user
    )

    # For create, an entry object doesn't exist yet, so a workspace is passed.
    # For update/review, an entry object exists, and we get the workspace from it.
    perm_object = workspace
    if entry:
        perm_object = entry.workspace

    # 1. Base permission check
    has_perm = user.has_perm(permission_to_check, perm_object)

    if not has_perm:
        raise PermissionDenied("You do not have permission to perform this action.")

    # 2. Role-specific checks (only for existing entries)
    if entry:
        actor_org_member = (
            actor.organization_member if isinstance(actor, TeamMember) else actor
        )

        # Submitter check
        if (
            permission_to_check == EntryPermissions.CHANGE_ENTRY
            and isinstance(actor, TeamMember)
            and actor.role == TeamMemberRole.SUBMITTER
            and entry.submitter != actor
        ):
            raise PermissionDenied("You can only edit your own entries.")

        # Team Coordinator check
        # A user who is a coordinator for any team is restricted to their own team's entries.
        if actor_org_member.coordinated_teams.exists():
            entry_team = entry.workspace_team.team if entry.workspace_team else None
            # If the entry is not associated with a team, or if the actor is not the
            # coordinator for that team, deny permission.
            if not entry_team or entry_team.team_coordinator != actor_org_member:
                raise PermissionDenied("You can only manage entries for your own team.")


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
    submitted_by_org_member = None,
    submitted_by_team_member = None,
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
    # currency = get_currency_by_code(currency_code)
    # if not currency:
    #     raise ValueError("Invalid currency code.")
    
    with transaction.atomic():
        # Create the Entry
        entry = Entry.objects.create(
            entry_type = entry_type,
            amount = amount,
            occurred_at = occurred_at,
            description = description,
            organization = organization,
            workspace = workspace or (workspace_team.workspace if workspace_team else None),
            workspace_team = workspace_team,
            currency = currency,
            exchange_rate_used = exchange_rate_used.rate,
            org_exchange_rate_ref = exchange_rate_used if isinstance(exchange_rate_used, OrganizationExchangeRate) else None,
            workspace_exchange_rate_ref = exchange_rate_used if isinstance(exchange_rate_used, WorkspaceExchangeRate) else None,
            submitted_by_org_member = submitted_by_org_member,
            submitted_by_team_member = submitted_by_team_member,
            is_flagged = not is_attachment_provided,
        )

        # Create the Attachments if any were provided
        if is_attachment_provided:
            create_attachments(
                entry=entry,
                attachments=attachments,
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
    replace_attachments: bool
):
    
    if entry.status != EntryStatus.PENDING:
        raise ValidationError("User can only update Entry info during the pending stage.")
    
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
            raise ValueError("No exchange rate is defined for the given currency and date.")
    
    # Update Provided Fields
    entry.amount = amount
    entry.currency = currency
    entry.occurred_at = occurred_at
    entry.description = description
    
    if new_exchange_rate_used:
        entry.exchange_rate_used = new_exchange_rate_used.rate
        entry.org_exchange_rate_ref = new_exchange_rate_used if isinstance(new_exchange_rate_used, OrganizationExchangeRate) else None
        entry.workspace_exchange_rate_ref = new_exchange_rate_used if isinstance(new_exchange_rate_used, WorkspaceExchangeRate) else None
            
    entry.save()
    
    # If new attachments were provided, replace existing ones or append the new ones
    if attachments:
        replace_or_append_attachments(
            entry=entry,
            attachments=attachments,
            replace_attachments=replace_attachments,
        )

        # If the entry was flagged, unflag it
        if entry.is_flagged:
            entry.is_flagged = False
            entry.save(update_fields=["is_flagged"])

def update_entry_status(
    *,
    entry: Entry,
    status,
    status_note,
    last_status_modified_by
):
    entry.status = status
    entry.status_note = status_note
    entry.last_status_modified_by = last_status_modified_by
    entry.status_last_updated_at = timezone.now()
    entry.save()

def delete_entry(entry):
    """
    Service to delete an entry.
    """

    if entry.reviewed_by:
        raise ValidationError("Cannot delete an entry that has been reviewed")

    if entry.status != EntryStatus.PENDING_REVIEW:
        raise ValidationError("Cannot delete an entry that is not pending review")

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
):
    """
    Service to create a new entry.
    """
    # Get workspace from workspace_team if workspace is not provided
    workspace = workspace or (workspace_team.workspace if workspace_team else None)

    # Validate workspace requirements based on entry type
    if entry_type == EntryType.WORKSPACE_EXP and not workspace:
        raise ValidationError("Workspace is required for workspace expense entries")

    _check_entry_permissions(
        actor=submitted_by,
        workspace=workspace,
        permission_to_check=EntryPermissions.ADD_ENTRY,
    )

    # If submitter is a team member, validate workspace_team for certain entry types
    if (
        isinstance(submitted_by, TeamMember)
        and entry_type
        in [EntryType.INCOME, EntryType.DISBURSEMENT, EntryType.REMITTANCE]
        and not workspace_team
    ):
        raise ValidationError("Workspace team is required for team-based entries")

    entry_data = {
        "entry_type": entry_type,
        "amount": amount,
        "description": description,
        "submitter_content_type": ContentType.objects.get_for_model(submitted_by),
        "submitter_object_id": submitted_by.pk,
        "workspace": workspace,
        "workspace_team": workspace_team,
    }

    entry = Entry()

    with transaction.atomic():
        entry = model_update(entry, entry_data)

        user = (
            submitted_by.organization_member.user
            if isinstance(submitted_by, TeamMember)
            else submitted_by.user
        )

        assign_perm(EntryPermissions.CHANGE_ENTRY, user, entry)
        assign_perm(EntryPermissions.DELETE_ENTRY, user, entry)
        assign_perm(EntryPermissions.UPLOAD_ATTACHMENTS, user, entry)

        audit_create(
            user=user,
            action_type="entry_created",
            target_entity=entry,
            metadata={
                "entry_type": entry_type,
                "amount": str(amount),
                "description": description,
            },
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


def entry_review(*, entry, reviewer, status, is_flagged=False, notes=None):
    """
    Service to review an entry (approve, reject, flag).
    """
    _check_entry_permissions(
        actor=reviewer,
        entry=entry,
        permission_to_check=EntryPermissions.REVIEW_ENTRY,
    )

    # Allow flagging with current status
    if is_flagged:
        if not notes:
            raise ValidationError("Notes are required when flagging an entry.")
    else:
        _validate_review_data(status=status, notes=notes)

    if not (
        entry.status == EntryStatus.PENDING_REVIEW
        or (is_flagged and entry.status == status)
    ):
        raise ValidationError(f"Cannot review entry with status: {entry.status}")

    entry.status = status
    entry.reviewed_by = reviewer
    entry.review_notes = notes or ""
    entry.is_flagged = is_flagged
    entry.save(update_fields=["status", "reviewed_by", "review_notes", "is_flagged"])

    audit_log_message = f"Entry {status.label.lower()} by {reviewer.user.username}"
    if notes:
        audit_log_message += f" with notes: {notes}"

    audit_create(
        user=reviewer.user,
        action_type=AuditActionType.STATUS_CHANGED,
        target_entity=entry,
        metadata={"message": audit_log_message},
    )

    return entry


def approve_entry(*, entry, reviewer, notes=None):
    """
    Service to approve an entry.
    """
    return entry_review(
        entry=entry, reviewer=reviewer, status=EntryStatus.APPROVED, notes=notes
    )


def reject_entry(*, entry, reviewer, notes):
    """
    Service to reject an entry.
    """
    return entry_review(
        entry=entry, reviewer=reviewer, status=EntryStatus.REJECTED, notes=notes
    )


def flag_entry(*, entry, reviewer, notes):
    """
    Service to flag an entry for further review.
    """
    return entry_review(
        entry=entry,
        reviewer=reviewer,
        status=entry.status,
        is_flagged=True,
        notes=notes,
    )


def bulk_review_entries(*, entries, reviewer, status, notes=None):
    """
    Service to review multiple entries at once.
    """
    _validate_review_data(status=status, notes=notes)

    reviewed_entries = []

    with transaction.atomic():
        for entry in entries:
            old_status = entry.status

            if entry.status != EntryStatus.PENDING_REVIEW and not entry.is_flagged:
                continue  # Skip entries that can't be reviewed

            entry_data = {
                "status": status,
                "reviewed_by": reviewer,
                "review_notes": notes or "",
            }

            entry = model_update(entry, entry_data)
            reviewed_entries.append(entry)

            if hasattr(reviewer, "organization_member"):
                audit_user = reviewer.organization_member.user
            else:
                audit_user = reviewer.user

            audit_create(
                user=audit_user,
                action_type="status_changed",
                target_entity=entry,
                metadata={
                    "old_status": old_status,
                    "new_status": status,
                    "review_notes": notes or "",
                    "bulk_operation": True,
                },
            )

    return reviewed_entries


def entry_update(*, entry, updated_by, **fields_to_update):
    """
    Service to update an existing entry.
    """
    _check_entry_permissions(
        actor=updated_by, entry=entry, permission_to_check=EntryPermissions.CHANGE_ENTRY
    )

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

    with transaction.atomic():
        entry = model_update(entry, update_data)

        audit_create(
            user=user,
            action_type="entry_updated",
            target_entity=entry,
            metadata={
                "updated_fields": list(update_data.keys()),
            },
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
