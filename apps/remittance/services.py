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
