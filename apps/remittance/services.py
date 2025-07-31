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
from apps.entries.selectors import get_total_amount_of_entries
from apps.workspaces.models import WorkspaceTeam


def handle_remittance_update(*, updated_entry: Entry, update_due_amount: bool):
    workspace_team = updated_entry.workspace_team
    remittance = workspace_team.remittance

    if update_due_amount:
        # Process due amount
        due_amount = process_due_amount(workspace_team, remittance)
        # Update the remittance record with the new due amount
        update_remittance_based_on_entry_status_change(
            remittance=remittance,
            due_amount=due_amount,
        )

    else:
        # Process paid amount
        remittance_total = get_total_amount_of_entries(
            entry_type=EntryType.REMITTANCE,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )

        # Update the remittance record with the new paid amount
        update_remittance_based_on_entry_status_change(
            remittance=remittance,
            paid_amount=remittance_total,
        )


def process_due_amount(workspace_team: WorkspaceTeam, remittance: Remittance):
    # 1. Sum all APPROVED INCOME entries for this team
    income_total = get_total_amount_of_entries(
        entry_type=EntryType.INCOME,
        entry_status=EntryStatus.APPROVED,
        workspace_team=workspace_team,
    )

    # 2. Sum all APPROVED DISBURSEMENT entries for this team
    disbursement_total = get_total_amount_of_entries(
        entry_type=EntryType.DISBURSEMENT,
        entry_status=EntryStatus.APPROVED,
        workspace_team=workspace_team,
    )

    # 3. Calculate final total: income - disbursements
    final_total = Decimal(income_total) - Decimal(disbursement_total)

    # 4. Get remittance rate from team or workspace
    print(f"===== > {workspace_team}")
    team_lvl_remittance_rate = workspace_team.custom_remittance_rate
    print(f"Team lvl remittance => {team_lvl_remittance_rate}")
    workspace_lvl_remittance_rate = workspace_team.workspace.remittance_rate
    print(f"Workspace lvl => {workspace_lvl_remittance_rate}")
    remittance_rate = (
        workspace_team.custom_remittance_rate
        if team_lvl_remittance_rate and team_lvl_remittance_rate != 0.00
        else workspace_team.workspace.remittance_rate
    )

    # Debug: Print calculation info
    print(f"Income Total: {income_total}")
    print(f"Disbursement Total: {disbursement_total}")
    print(f"Remittance Rate: {remittance_rate} {type(remittance_rate)}")
    print(f"Final Total: {final_total} {type(final_total)}")

    # 5. Apply rate to get due amount
    due_amount = 0
    if final_total > 0:
        due_amount = final_total * (remittance_rate * Decimal("0.01"))

    return due_amount


def update_remittance_based_on_entry_status_change(
    *, remittance: Remittance, due_amount=None, paid_amount=None
):
    print(
        f"Pre-Update Remittance: {remittance.due_amount} | {remittance.paid_amount} | {remittance.status} | {remittance.is_overpaid}"
    )

    # Debug: Show the values we’re about to apply
    print(f"Values to update with: {due_amount} | {paid_amount}")

    # Update only the fields that are provided
    remittance.due_amount = (
        due_amount if due_amount is not None else remittance.due_amount
    )
    remittance.paid_amount = (
        paid_amount if paid_amount is not None else remittance.paid_amount
    )
    remittance.update_status()
    remittance.check_if_overdue()
    remittance.check_if_overpaid()

    # Debug: Show values before saving

    # Save the updated fields to the database
    remittance.save(
        update_fields=[
            "due_amount",
            "paid_amount",
            "status",
            "paid_within_deadlines",
            "is_overpaid",
        ]
    )

    # Debug: Confirm saved values
    print(
        f"Post-Update Remittance: {remittance.due_amount} | {remittance.paid_amount} | {remittance.status} | {remittance.is_overpaid}"
    )


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
