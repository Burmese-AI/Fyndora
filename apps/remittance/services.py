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
from apps.invitations.selectors import get_organization_member_by_user_and_organization


def update_remittance_based_on_entry_status_change(
    *, remittance: Remittance, due_amount=None, paid_amount=None
):
    print(f"Values to update with: {due_amount} | {paid_amount}")
    remittance.due_amount = (
        due_amount if due_amount is not None else remittance.due_amount
    )
    remittance.paid_amount = (
        paid_amount if paid_amount is not None else remittance.paid_amount
    )
    print(f"Pre-Update Remittance: {remittance.due_amount} | {remittance.paid_amount}")
    remittance.save(update_fields=["due_amount", "paid_amount"])
    print(f"Post-Update Remittance: {remittance.due_amount} | {remittance.paid_amount}")


def handle_remittance_update(*, updated_entry: Entry, update_due_amount: bool):
    workspace_team = updated_entry.workspace_team
    remittance = workspace_team.remittance

    if update_due_amount:
        print("Update Due Amount")
        # Get the total of all approved INCOME entries and DISBURSEMENT entries
        income_total = get_total_amount_of_entries(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )
        disbursement_total = get_total_amount_of_entries(
            entry_type=EntryType.DISBURSEMENT,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )
        # Get the final total amount (INCOME - DISBURSEMENT)
        final_total = Decimal(income_total) - Decimal(disbursement_total)
        # Multiply it by the remittance rate (Org or Team)
        remittance_rate = (
            workspace_team.custom_remittance_rate
            if workspace_team.custom_remittance_rate != 0.00
            else workspace_team.workspace.remittance_rate
        )
        print(f"Income Total: {income_total}")
        print(f"Disbursement Total: {disbursement_total}")
        print(f"Remittance Rate: {remittance_rate} {type(remittance_rate)}")
        print(f"Final Total: {final_total} {type(final_total)}")
        due_amount = final_total * (remittance_rate * Decimal("0.01"))
        # Call update_remittance_based_on_entry_status_change
        update_remittance_based_on_entry_status_change(
            remittance=remittance,
            due_amount=due_amount,
        )
    else:
        print("Update Paid Amount")
        # Get the total of all approved REMITTANCE entries
        remittance_total = get_total_amount_of_entries(
            entry_type=EntryType.REMITTANCE,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )
        # Call update_remittance_based_on_entry_status_change
        update_remittance_based_on_entry_status_change(
            remittance=remittance,
            paid_amount=remittance_total,
        )


def remittance_confirm_payment(*, remittance, user, skip_permissions=False):
    """
    Confirms a remittance payment.
    """
    if not skip_permissions:
        workspace = remittance.workspace_team.workspace
        if not user.has_perm(RemittancePermissions.REVIEW_REMITTANCE, workspace):
            raise PermissionDenied("You do not have permission to confirm this remittance.")

    if remittance.paid_amount < remittance.due_amount:
        raise ValidationError(
            "Cannot confirm payment: The due amount has not been fully paid."
        )

    # Get the OrganizationMember instance for the user
    organization_member = get_organization_member_by_user_and_organization(
        user=user, 
        organization=remittance.workspace_team.workspace.organization
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
    if not user.has_perm(RemittancePermissions.CHANGE_REMITTANCE, workspace):
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

    # Check if remittance is now overdue
    remittance.check_if_overdue()
    remittance.save(update_fields=["paid_within_deadlines"])

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

    remittance.status = RemittanceStatus.CANCELED
    remittance.save(update_fields=["status"])

    return remittance
