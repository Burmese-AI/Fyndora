from decimal import Decimal
from tkinter import N

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.utils import model_update
from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.entries.selectors import get_total_amount_of_entries
from apps.organizations.selectors import get_orgMember_by_user_id_and_organization_id
from apps.remittance.constants import RemittanceStatus
from apps.remittance.exceptions import RemittanceConfirmPaymentException
from apps.remittance.models import Remittance
from apps.remittance.permissions import RemittancePermissions
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
    team_lvl_remittance_rate = workspace_team.custom_remittance_rate
    remittance_rate = (
        workspace_team.custom_remittance_rate
        if team_lvl_remittance_rate and team_lvl_remittance_rate != 0.00
        else workspace_team.workspace.remittance_rate
    )

    # 5. Apply rate to get due amount
    due_amount = 0
    if final_total > 0:
        due_amount = final_total * (remittance_rate * Decimal("0.01"))

    return due_amount


def update_remittance_based_on_entry_status_change(
    *, remittance: Remittance, due_amount=None, paid_amount=None
):
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


def remittance_confirm_payment(*, remittance, user, organization_id):
    """
    Confirms a remittance payment.
    """

    # if remittance.paid_amount < remittance.due_amount:
    #     raise RemittanceConfirmPaymentException(
    #         "Cannot confirm payment: The due amount has not been fully paid."
    #     )

    # if the remittance is already confirmed, then we need to update the confirmed_by and confirmed_at fields which means we have to remove the confirmed_by field and set it to None
    if remittance.confirmed_by:
        organization_member = None;
    else:
        organization_member = get_orgMember_by_user_id_and_organization_id(
            user_id=user.pk,
            organization_id=organization_id,
        )

    updated_remittance = model_update(
        instance=remittance,
        update_fields=["confirmed_by", "confirmed_at"],
        data={
            "confirmed_by": organization_member,
            "confirmed_at": timezone.now(),
        },
    )

    return updated_remittance


def remittance_record_payment(*, remittance, user, amount):
    """
    Records a payment against a remittance.
    """
    workspace = remittance.workspace_team.workspace

    if remittance.status in [RemittanceStatus.PAID, RemittanceStatus.CANCELED]:
        raise ValidationError(
            f"Cannot record a payment for a remittance with status '{remittance.status}'."
        )

    if remittance.paid_amount + amount > remittance.due_amount:
        remaining_amount = remittance.due_amount - remittance.paid_amount
        raise ValidationError(
            f"Payment of {amount} exceeds the remaining due amount of {remaining_amount}."
        )

    # Update payment amount and recalculate status
    remittance.paid_amount += amount
    remittance.update_status()
    remittance.check_if_overdue()
    remittance.check_if_overpaid()

    remittance.save(
        update_fields=["paid_amount", "status", "paid_within_deadlines", "is_overpaid"]
    )

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
            remittance.update_status()
            remittance.check_if_overdue()
            remittance.check_if_overpaid()
            remittance.save(
                update_fields=[
                    "due_amount",
                    "status",
                    "paid_within_deadlines",
                    "is_overpaid",
                ]
            )
        else:
            remittance = Remittance.objects.create(
                workspace_team=workspace_team,
                due_amount=due_amount_to_add,
                status=RemittanceStatus.PENDING,
            )

    return remittance


def remittance_change_due_date(*, remittance, user, due_date):
    """
    Updates the due date of a remittance by changing the workspace end date.
    """
    workspace = remittance.workspace_team.workspace
    if not user.has_perm(RemittancePermissions.CHANGE_REMITTANCE, workspace):
        raise PermissionDenied(
            "You do not have permission to change the due date for this remittance."
        )

    if remittance.status in [RemittanceStatus.PAID, RemittanceStatus.CANCELED]:
        raise ValidationError(
            f"Cannot update a remittance with status '{remittance.status}'."
        )

    # Update the workspace end_date which serves as the due date
    workspace = remittance.workspace_team.workspace
    workspace.end_date = due_date
    workspace.full_clean()
    workspace.save(update_fields=["end_date"])

    # Update status and check all conditions after due date change
    remittance.update_status()
    remittance.check_if_overdue()
    remittance.check_if_overpaid()
    remittance.save(update_fields=["status", "paid_within_deadlines", "is_overpaid"])

    return remittance


def remittance_create(user, workspace_team, due_amount, description=None):
    """
    Manually creates a new remittance record.
    """
    # For creation, we need to check against the workspace since remittance doesn't exist yet
    workspace = workspace_team.workspace
    if not user.has_perm(RemittancePermissions.ADD_REMITTANCE, workspace):
        raise PermissionDenied("You do not have permission to create a remittance.")

    if due_amount <= 0:
        raise ValidationError("Due amount must be positive.")

    remittance = Remittance(
        workspace_team=workspace_team,
        due_amount=due_amount,
        status=RemittanceStatus.PENDING,
    )

    remittance.full_clean()
    remittance.save()

    return remittance


def remittance_cancel(*, remittance, user):
    """
    Cancels a remittance.
    """
    workspace = remittance.workspace_team.workspace
    if not user.has_perm(RemittancePermissions.DELETE_REMITTANCE, workspace):
        raise PermissionDenied("You do not have permission to cancel this remittance.")

    if remittance.paid_amount > 0:
        raise ValidationError("Cannot cancel a remittance that has payments recorded.")

    if remittance.status == RemittanceStatus.CANCELED:
        return remittance

    # Set status to canceled and update related fields
    remittance.status = RemittanceStatus.CANCELED
    remittance.check_if_overdue()
    remittance.check_if_overpaid()
    remittance.save(update_fields=["status", "paid_within_deadlines", "is_overpaid"])

    return remittance
