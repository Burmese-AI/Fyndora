from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.utils import model_update
from apps.entries.models import EntryType
from apps.entries.permissions import EntryPermissions
from apps.remittance.models import Remittance


def remittance_confirm_payment(*, remittance, user):
    """
    Confirms a remittance payment.
    """
    if not user.has_perm(EntryPermissions.REVIEW_ENTRY):
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


def remittance_record_payment(*, remittance, amount, user):
    """
    Records a payment against a remittance.
    """
    if not user.has_perm(EntryPermissions.CHANGE_ENTRY):
        raise PermissionDenied(
            "You do not have permission to record a payment for this remittance."
        )

    if amount <= 0:
        raise ValidationError("Payment amount must be positive.")

    if remittance.status in ["paid", "canceled"]:
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

    team = workspace_team.team
    workspace = workspace_team.workspace

    rate = (
        team.custom_remittance_rate
        if team.custom_remittance_rate is not None
        else workspace.remittance_rate
    )
    if rate is None:
        return None

    remittance_rate = Decimal(str(rate)) / Decimal("100.00")
    due_amount_to_add = entry.amount * remittance_rate

    with transaction.atomic():
        remittance, created = Remittance.objects.get_or_create(
            workspace_team=workspace_team,
            status="pending",
            defaults={
                "due_amount": due_amount_to_add,
                "due_date": workspace.end_date,
            },
        )

        if not created:
            remittance.due_amount += due_amount_to_add
            remittance.save(update_fields=["due_amount"])

    return remittance


def remittance_update(*, remittance, user, data):
    """
    Updates a remittance instance.
    """
    if not user.has_perm(EntryPermissions.REVIEW_ENTRY):
        raise PermissionDenied("You do not have permission to update this remittance.")

    if remittance.status in ["paid", "canceled"]:
        raise ValidationError(
            f"Cannot update a remittance with status '{remittance.status}'."
        )

    for field_name, value in data.items():
        setattr(remittance, field_name, value)

    remittance.full_clean()
    remittance.save()

    return remittance


def remittance_create(
    *, user, workspace_team, due_amount, due_date, status="pending"
):
    """
    Manually creates a new remittance record.
    """
    if not user.has_perm(EntryPermissions.REVIEW_ENTRY):
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
    if not user.has_perm(EntryPermissions.DELETE_ENTRY):
        raise PermissionDenied("You do not have permission to cancel this remittance.")

    if remittance.paid_amount > 0:
        raise ValidationError("Cannot cancel a remittance that has payments recorded.")

    if remittance.status == "canceled":
        return remittance

    remittance.status = "canceled"
    remittance.save(update_fields=["status"])

    return remittance
