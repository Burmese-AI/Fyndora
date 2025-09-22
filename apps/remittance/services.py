from decimal import Decimal

from django.utils import timezone

from apps.core.utils import handle_service_errors, model_update
from apps.auditlog.constants import AuditActionType
from apps.auditlog.services import audit_create
from apps.entries.constants import EntryStatus, EntryType
from apps.entries.selectors import get_total_amount_of_entries
from apps.organizations.selectors import get_orgMember_by_user_id_and_organization_id
from apps.remittance.exceptions import RemittanceServiceError
from apps.remittance.models import Remittance
from apps.workspaces.models import WorkspaceTeam


class RemittanceService:
    @staticmethod
    @handle_service_errors(RemittanceServiceError)
    def sync_remittance(
        *,
        workspace_team: WorkspaceTeam,
        calc_due_amt: bool = True,
        calc_paid_amt: bool = True,
    ):
        remittance = workspace_team.remittance
        required_to_update = False

        if calc_due_amt:
            remittance.due_amount = RemittanceService._calculate_due_amount(
                workspace_team=workspace_team
            )
            required_to_update = True

        if calc_paid_amt:
            remittance.paid_amount = RemittanceService._calculate_paid_amount(
                workspace_team=workspace_team
            )
            required_to_update = True

        if required_to_update:
            RemittanceService.update_remittance(remittance=remittance)

        return remittance

    @staticmethod
    @handle_service_errors(RemittanceServiceError)
    def bulk_sync_remittance(
        *,
        workspace_teams: list[WorkspaceTeam],
        calc_due_amt: bool = True,
        calc_paid_amt: bool = True,
    ) -> list[Remittance]:
        remittances = []
        required_to_update = False

        # TODO: Hidden N + 1 problem here
        for workspace_team in workspace_teams:
            required_to_update = False
            remittance = workspace_team.remittance

            if calc_due_amt:
                remittance.due_amount = RemittanceService._calculate_due_amount(
                    workspace_team=remittance.workspace_team
                )
                required_to_update = True

            if calc_paid_amt:
                remittance.paid_amount = RemittanceService._calculate_paid_amount(
                    workspace_team=remittance.workspace_team
                )
                required_to_update = True

            if required_to_update:
                remittances.append(remittance)

        return RemittanceService.bulk_update_remittance(remittances=remittances)

    @staticmethod
    @handle_service_errors(RemittanceServiceError)
    def _calculate_due_amount(*, workspace_team: WorkspaceTeam):
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

    @staticmethod
    @handle_service_errors(RemittanceServiceError)
    def _calculate_paid_amount(*, workspace_team: WorkspaceTeam):
        """
        Calculate the paid amount for a workspace team.
        """
        return get_total_amount_of_entries(
            entry_type=EntryType.REMITTANCE,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )

    @staticmethod
    @handle_service_errors(RemittanceServiceError)
    def update_remittance(*, remittance: Remittance):
        """
        Update the remittance status and other fields.
        """
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

    @staticmethod
    @handle_service_errors(RemittanceServiceError)
    def bulk_update_remittance(*, remittances: list[Remittance]) -> list[Remittance]:
        """
        Bulk update the remittance status and other fields.
        """
        Remittance.objects.bulk_update(
            remittances,
            [
                "due_amount",
                "paid_amount",
                "status",
                "paid_within_deadlines",
                "is_overpaid",
            ],
        )
        return remittances

    @staticmethod
    @handle_service_errors(RemittanceServiceError)
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

        # Log audit trail for remittance confirmation/unconfirmation
        is_confirming = organization_member is not None
        audit_create(
            user=user,
            action_type=AuditActionType.REMITTANCE_CONFIRMED,
            target_entity=updated_remittance,
            metadata={
                "action": "confirmed" if is_confirming else "unconfirmed",
                "remittance_id": str(updated_remittance.remittance_id),
                "workspace_team_id": str(
                    updated_remittance.workspace_team.workspace_team_id
                ),
                "organization_id": str(organization_id),
                "due_amount": str(updated_remittance.due_amount),
                "paid_amount": str(updated_remittance.paid_amount),
                "confirmed_by": str(organization_member.organization_member_id)
                if organization_member
                else None,
                "confirmed_at": updated_remittance.confirmed_at.isoformat()
                if updated_remittance.confirmed_at
                else None,
            },
        )

        return updated_remittance
