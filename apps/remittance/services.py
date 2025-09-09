from decimal import Decimal

from django.utils import timezone

from apps.core.utils import model_update
from apps.entries.constants import EntryStatus, EntryType
from apps.entries.selectors import get_total_amount_of_entries
from apps.organizations.selectors import get_orgMember_by_user_id_and_organization_id
from apps.remittance.models import Remittance
from apps.workspaces.models import WorkspaceTeam


def calculate_due_amount(*, workspace_team: WorkspaceTeam):
    """
    Calculate the due amount for a workspace team.
    """
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
    # 4. Get remittance rate from team
    team_lvl_remittance_rate = workspace_team.custom_remittance_rate
    remittance_rate = (
        team_lvl_remittance_rate
        if team_lvl_remittance_rate
        else workspace_team.workspace.remittance_rate
    )
    # 5. Apply rate to get due amount
    due_amount = (
        0 if final_total <= 0 else final_total * (remittance_rate * Decimal("0.01"))
    )

    return due_amount


def calculate_paid_amount(*, workspace_team: WorkspaceTeam):
    return get_total_amount_of_entries(
        entry_type=EntryType.REMITTANCE,
        entry_status=EntryStatus.APPROVED,
        workspace_team=workspace_team,
    )


def update_remittance(*, remittance: Remittance):
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


def bulk_update_remittance(*, remittances: list[Remittance]):
    Remittance.objects.bulk_update(
        remittances,
        [
            "due_amount", 
            "paid_amount", 
            "status", 
            "paid_within_deadlines", 
            "is_overpaid"
        ],
    )
    return remittances


def remittance_confirm_payment(*, remittance, user, organization_id):
    """
    Confirms a remittance payment.
    """
    # I think we should allow the user to decide whether to confirm the payment or not rather than denying form the system... i specifically added warning message in the template
    # if remittance.paid_amount < remittance.due_amount:
    #     raise RemittanceConfirmPaymentException(
    #         "Cannot confirm payment: The due amount has not been fully paid."
    #     )

    # if the remittance is already confirmed, then we need to update the confirmed_by and confirmed_at fields which means we have to remove the confirmed_by field and set it to None
    if remittance.confirmed_by:
        organization_member = None
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
