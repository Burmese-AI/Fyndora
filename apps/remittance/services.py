from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.utils import model_update
from apps.remittance.permissions import RemittancePermissions
from apps.remittance.models import Remittance
from apps.remittance.constants import RemittanceStatus
from apps.entries.models import Entry
from apps.entries.constants import EntryType, EntryStatus


def update_remittance_based_on_entry_status_change(old_entry: Entry, new_entry: Entry):
    remittance = new_entry.workspace_team.remittance

    if not old_entry:
        if new_entry.status == EntryStatus.APPROVED:
            _apply_approved_effect(new_entry, remittance)
    else:
        status_changed = old_entry.status != new_entry.status
        amount_changed = old_entry.amount != new_entry.amount

        if amount_changed:
            raise ValidationError("Amount cannot be changed after approval")

        # Revert old effect only if status was APPROVED
        if old_entry.status == EntryStatus.APPROVED and status_changed:
            revert_approved_effect(old_entry, remittance)

        # Apply new effect if status is APPROVED now
        if new_entry.status == EntryStatus.APPROVED and status_changed:
            apply_approved_effect(new_entry, remittance)

    remittance.save()


def apply_approved_effect(entry: Entry, remittance):
    if entry.entry_type in [EntryType.INCOME]:
        remittance.due_amount += entry.amount
    elif entry.entry_type == EntryType.REMITTANCE:
        remittance.paid_amount += entry.amount


def revert_approved_effect(entry: Entry, remittance):
    if entry.entry_type in [EntryType.INCOME]:
        remittance.due_amount -= entry.amount
    elif entry.entry_type == EntryType.REMITTANCE:
        remittance.paid_amount -= entry.amount


def remittance_confirm_payment(*, remittance, user):
    """
    Confirms a remittance payment.
    """
    if not user.has_perm(RemittancePermissions.REVIEW_REMITTANCE):
        raise PermissionDenied("You do not have permission to confirm this remittance.")

    if remittance.paid_amount < remittance.due_amount:
        raise ValidationError(
            "Cannot confirm payment: The due amount has not been fully paid."
        )

    updated_remittance = model_update(
        instance=remittance,
        fields=["confirmed_by", "confirmed_at"],
        data={
            "confirmed_by": user,
            "confirmed_at": timezone.now(),
        },
    )

    return updated_remittance


def remittance_record_payment(*, remittance, user, amount):
    """
    Records a payment against a remittance.
    """
    if not user.has_perm(RemittancePermissions.CHANGE_REMITTANCE):
        raise PermissionDenied(
            "You do not have permission to record a payment for this remittance."
        )

    if remittance.status in [RemittanceStatus.PAID, RemittanceStatus.CANCELED]:
        raise ValidationError(
            f"Cannot record a payment for a remittance with status '{remittance.status}'."
        )

    if remittance.paid_amount + amount > remittance.due_amount:
        remaining_amount = remittance.due_amount - remittance.paid_amount
        raise ValidationError(
            f"Payment of {amount} exceeds the remaining due amount of {remaining_amount}."
        )

    remittance.paid_amount += amount
    remittance.save(update_fields=["paid_amount", "status"])

    return remittance


def remittance_create_or_update_from_income_entry(*, entry):
    """
    Creates or updates a remittance based on a new income Entry.
    """
    if entry.entry_type != EntryType.INCOME:
        return None

    workspace_team = entry.workspace_team
    if not workspace_team:
        return None

    workspace = workspace_team.workspace

    rate = (
        workspace_team.custom_remittance_rate
        if workspace_team.custom_remittance_rate is not None
        else workspace.remittance_rate
    )
    if rate is None:
        return None

    remittance_rate = Decimal(str(rate)) / Decimal("100.00")
    due_amount_to_add = entry.amount * remittance_rate

    with transaction.atomic():
        remittance = (
            Remittance.objects.filter(workspace_team=workspace_team)
            .exclude(status__in=[RemittanceStatus.PAID, RemittanceStatus.CANCELED])
            .first()
        )

        if remittance:
            remittance.due_amount += due_amount_to_add
            remittance.save(update_fields=["due_amount"])
        else:
            remittance = Remittance.objects.create(
                workspace_team=workspace_team,
                due_amount=due_amount_to_add,
                due_date=workspace.end_date,
                status=RemittanceStatus.PENDING,
            )

    return remittance


def remittance_change_due_date(*, remittance, user, due_date):
    """
    Updates the due date of a remittance.
    """
    if not user.has_perm(RemittancePermissions.CHANGE_REMITTANCE):
        raise PermissionDenied(
            "You do not have permission to change the due date for this remittance."
        )

    if remittance.status in [RemittanceStatus.PAID, RemittanceStatus.CANCELED]:
        raise ValidationError(
            f"Cannot update a remittance with status '{remittance.status}'."
        )

    remittance.due_date = due_date
    remittance.full_clean()
    remittance.save(update_fields=["due_date", "status"])

    return remittance


def remittance_create(
    *, user, workspace_team, due_amount, due_date, status=RemittanceStatus.PENDING
):
    """
    Manually creates a new remittance record.
    """
    if not user.has_perm(RemittancePermissions.ADD_REMITTANCE):
        raise PermissionDenied("You do not have permission to create a remittance.")

    if due_amount <= 0:
        raise ValidationError("Due amount must be positive.")

    remittance = Remittance(
        workspace_team=workspace_team,
        due_amount=due_amount,
        due_date=due_date,
        status=status,
    )

    remittance.full_clean()
    remittance.save()

    return remittance


def remittance_cancel(*, remittance, user):
    """
    Cancels a remittance.
    """
    if not user.has_perm(RemittancePermissions.DELETE_REMITTANCE):
        raise PermissionDenied("You do not have permission to cancel this remittance.")

    if remittance.paid_amount > 0:
        raise ValidationError("Cannot cancel a remittance that has payments recorded.")

    if remittance.status == RemittanceStatus.CANCELED:
        return remittance

    remittance.status = RemittanceStatus.CANCELED
    remittance.save(update_fields=["status"])

    return remittance
