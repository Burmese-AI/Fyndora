"""
Unit tests for Remittance services.
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest
from django.utils import timezone

from apps.remittance.services import RemittanceService
from apps.remittance.constants import RemittanceStatus
from apps.remittance.models import Remittance
from apps.entries.constants import EntryStatus, EntryType
from apps.auditlog.constants import AuditActionType
from tests.factories import (
    WorkspaceTeamFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
)


@pytest.mark.django_db
class TestCalculateDueAmount:
    """Test _calculate_due_amount service method."""

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_due_amount_positive_income(self, mock_get_entries):
        """Test due amount calculation with positive income."""
        # Mock the entries selector
        mock_get_entries.side_effect = [
            Decimal("1000.00"),  # Income total
            Decimal("300.00"),  # Disbursement total
        ]

        workspace_team = WorkspaceTeamFactory()
        workspace_team.custom_remittance_rate = 15  # 15%
        workspace_team.save()

        result = RemittanceService._calculate_due_amount(workspace_team=workspace_team)

        # Expected: (1000 - 300) * 0.15 = 105.00
        expected_due = Decimal("105.00")
        assert result == expected_due

        # Verify the selector was called correctly
        assert mock_get_entries.call_count == 2
        mock_get_entries.assert_any_call(
            entry_type=EntryType.INCOME,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )
        mock_get_entries.assert_any_call(
            entry_type=EntryType.DISBURSEMENT,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_due_amount_negative_income(self, mock_get_entries):
        """Test due amount calculation with negative income (no due amount)."""
        mock_get_entries.side_effect = [
            Decimal("300.00"),  # Income total
            Decimal("1000.00"),  # Disbursement total
        ]

        workspace_team = WorkspaceTeamFactory()
        workspace_team.custom_remittance_rate = 20  # 20%
        workspace_team.save()

        result = RemittanceService._calculate_due_amount(workspace_team=workspace_team)

        # When income < disbursements, due amount should be 0
        assert result == Decimal("0.00")

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_due_amount_zero_income(self, mock_get_entries):
        """Test due amount calculation with zero income."""
        mock_get_entries.side_effect = [
            Decimal("0.00"),  # Income total
            Decimal("0.00"),  # Disbursement total
        ]

        workspace_team = WorkspaceTeamFactory()
        workspace_team.custom_remittance_rate = 25  # 25%
        workspace_team.save()

        result = RemittanceService._calculate_due_amount(workspace_team=workspace_team)

        # When income = disbursements, due amount should be 0
        assert result == Decimal("0.00")

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_due_amount_uses_workspace_rate_when_no_custom_rate(
        self, mock_get_entries
    ):
        """Test that workspace remittance rate is used when no custom rate is set."""
        mock_get_entries.side_effect = [
            Decimal("1000.00"),  # Income total
            Decimal("200.00"),  # Disbursement total
        ]

        workspace_team = WorkspaceTeamFactory()
        workspace_team.custom_remittance_rate = None  # No custom rate
        workspace_team.save()

        # Set workspace remittance rate
        workspace_team.workspace.remittance_rate = 18  # 18%
        workspace_team.workspace.save()

        result = RemittanceService._calculate_due_amount(workspace_team=workspace_team)

        # Expected: (1000 - 200) * 0.18 = 144.00
        expected_due = Decimal("144.00")
        assert result == expected_due

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_due_amount_custom_rate_priority(self, mock_get_entries):
        """Test that custom remittance rate takes priority over workspace rate."""
        mock_get_entries.side_effect = [
            Decimal("1000.00"),  # Income total
            Decimal("100.00"),  # Disbursement total
        ]

        workspace_team = WorkspaceTeamFactory()
        workspace_team.custom_remittance_rate = 25  # 25% custom rate
        workspace_team.save()

        # Set different workspace remittance rate
        workspace_team.workspace.remittance_rate = 15  # 15% workspace rate
        workspace_team.workspace.save()

        result = RemittanceService._calculate_due_amount(workspace_team=workspace_team)

        # Should use custom rate: (1000 - 100) * 0.25 = 225.00
        expected_due = Decimal("225.00")
        assert result == expected_due

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_due_amount_decimal_precision(self, mock_get_entries):
        """Test due amount calculation maintains proper decimal precision."""
        mock_get_entries.side_effect = [
            Decimal("1234.56"),  # Income total
            Decimal("234.56"),  # Disbursement total
        ]

        workspace_team = WorkspaceTeamFactory()
        workspace_team.custom_remittance_rate = Decimal("12.5")  # 12.5%
        workspace_team.save()

        result = RemittanceService._calculate_due_amount(workspace_team=workspace_team)

        # Expected: (1234.56 - 234.56) * 0.125 = 125.00
        expected_due = Decimal("125.00")
        assert result == expected_due


@pytest.mark.django_db
class TestCalculatePaidAmount:
    """Test _calculate_paid_amount service method."""

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_paid_amount(self, mock_get_entries):
        """Test paid amount calculation."""
        mock_get_entries.return_value = Decimal("500.00")

        workspace_team = WorkspaceTeamFactory()

        result = RemittanceService._calculate_paid_amount(workspace_team=workspace_team)

        assert result == Decimal("500.00")
        mock_get_entries.assert_called_once_with(
            entry_type=EntryType.REMITTANCE,
            entry_status=EntryStatus.APPROVED,
            workspace_team=workspace_team,
        )

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_paid_amount_zero(self, mock_get_entries):
        """Test paid amount calculation when no payments exist."""
        mock_get_entries.return_value = Decimal("0.00")

        workspace_team = WorkspaceTeamFactory()

        result = RemittanceService._calculate_paid_amount(workspace_team=workspace_team)

        assert result == Decimal("0.00")


@pytest.mark.django_db
class TestUpdateRemittance:
    """Test update_remittance service method."""

    def test_update_remittance_updates_all_fields(self):
        """Test that update_remittance calls all required methods and saves."""
        workspace_team = WorkspaceTeamFactory()
        # Get the signal-created remittance
        remittance = Remittance.objects.get(workspace_team=workspace_team)

        # Mock the remittance methods to verify they're called
        with (
            patch.object(remittance, "update_status") as mock_update_status,
            patch.object(remittance, "check_if_overdue") as mock_check_overdue,
            patch.object(remittance, "check_if_overpaid") as mock_check_overpaid,
            patch.object(remittance, "save") as mock_save,
        ):
            RemittanceService.update_remittance(remittance=remittance)

            # Verify all methods were called
            mock_update_status.assert_called_once()
            mock_check_overdue.assert_called_once()
            mock_check_overpaid.assert_called_once()

            # Verify save was called with correct update_fields
            mock_save.assert_called_once_with(
                update_fields=[
                    "due_amount",
                    "paid_amount",
                    "status",
                    "paid_within_deadlines",
                    "is_overpaid",
                ]
            )

    def test_update_remittance_with_real_data(self):
        """Test update_remittance with actual data changes."""
        workspace_team = WorkspaceTeamFactory()
        # Get the signal-created remittance
        remittance = Remittance.objects.get(workspace_team=workspace_team)

        # Update the remittance with test data
        remittance.due_amount = Decimal("1000.00")
        remittance.paid_amount = Decimal("500.00")
        remittance.status = RemittanceStatus.PENDING
        remittance.save()

        # Update the remittance
        RemittanceService.update_remittance(remittance=remittance)

        # Refresh from database
        remittance.refresh_from_db()

        # Status should be updated to PARTIAL
        assert remittance.status == RemittanceStatus.PARTIAL
        # Other fields should be updated based on the model methods
        assert hasattr(remittance, "paid_within_deadlines")
        assert hasattr(remittance, "is_overpaid")


@pytest.mark.django_db
class TestRemittanceConfirmPayment:
    """Test remittance_confirm_payment service method."""

    @patch("apps.remittance.services.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.remittance.services.model_update")
    @patch("apps.remittance.services.audit_create")
    def test_remittance_confirm_payment_first_time(
        self, mock_audit_create, mock_model_update, mock_get_org_member
    ):
        """Test confirming payment for the first time."""
        # Setup
        organization = OrganizationFactory()
        user = CustomUserFactory()
        organization_member = OrganizationMemberFactory(
            organization=organization, user=user
        )

        # Create a workspace team and get its signal-created remittance
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        remittance.confirmed_by = None
        remittance.confirmed_at = None
        remittance.save()

        mock_get_org_member.return_value = organization_member
        mock_model_update.return_value = remittance

        # Execute
        result = RemittanceService.remittance_confirm_payment(
            remittance=remittance,
            user=user,
            organization_id=organization.organization_id,
        )

        # Verify
        mock_get_org_member.assert_called_once_with(
            user_id=user.pk, organization_id=organization.organization_id
        )
        mock_model_update.assert_called_once_with(
            instance=remittance,
            update_fields=["confirmed_by", "confirmed_at"],
            data={
                "confirmed_by": organization_member,
                "confirmed_at": mock_model_update.call_args[1]["data"]["confirmed_at"],
            },
        )
        
        # Verify audit log was created
        mock_audit_create.assert_called_once()
        audit_call_args = mock_audit_create.call_args
        assert audit_call_args[1]["user"] == user
        assert audit_call_args[1]["action_type"] == AuditActionType.REMITTANCE_CONFIRMED
        assert audit_call_args[1]["target_entity"] == remittance
        assert audit_call_args[1]["metadata"]["action"] == "confirmed"
        
        assert result == remittance

    @patch("apps.remittance.services.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.remittance.services.model_update")
    @patch("apps.remittance.services.audit_create")
    def test_remittance_confirm_payment_already_confirmed(
        self, mock_audit_create, mock_model_update, mock_get_org_member
    ):
        """Test confirming payment when already confirmed (should unconfirm)."""
        # Setup
        organization = OrganizationFactory()
        user = CustomUserFactory()
        organization_member = OrganizationMemberFactory(
            organization=organization, user=user
        )

        # Create a workspace team and get its signal-created remittance
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        remittance.confirmed_by = organization_member
        remittance.confirmed_at = timezone.now()
        remittance.save()

        mock_model_update.return_value = remittance

        # Execute
        result = RemittanceService.remittance_confirm_payment(
            remittance=remittance,
            user=user,
            organization_id=organization.organization_id,
        )

        # Verify
        # Should not call get_orgMember since we're unconfirming
        mock_get_org_member.assert_not_called()
        mock_model_update.assert_called_once_with(
            instance=remittance,
            update_fields=["confirmed_by", "confirmed_at"],
            data={
                "confirmed_by": None,
                "confirmed_at": mock_model_update.call_args[1]["data"]["confirmed_at"],
            },
        )
        
        # Verify audit log was created for unconfirmation
        mock_audit_create.assert_called_once()
        audit_call_args = mock_audit_create.call_args
        assert audit_call_args[1]["metadata"]["action"] == "unconfirmed"
        
        assert result == remittance

    @patch("apps.remittance.services.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.remittance.services.model_update")
    @patch("apps.remittance.services.audit_create")
    def test_remittance_confirm_payment_organization_member_not_found(
        self, mock_audit_create, mock_model_update, mock_get_org_member
    ):
        """Test confirming payment when organization member is not found."""
        # Setup
        organization = OrganizationFactory()
        user = CustomUserFactory()

        # Create a workspace team and get its signal-created remittance
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        remittance.confirmed_by = None
        remittance.confirmed_at = None
        remittance.save()

        mock_get_org_member.return_value = None
        mock_model_update.return_value = remittance

        # Execute
        result = RemittanceService.remittance_confirm_payment(
            remittance=remittance,
            user=user,
            organization_id=organization.organization_id,
        )

        # Verify
        mock_get_org_member.assert_called_once_with(
            user_id=user.pk, organization_id=organization.organization_id
        )
        mock_model_update.assert_called_once_with(
            instance=remittance,
            update_fields=["confirmed_by", "confirmed_at"],
            data={
                "confirmed_by": None,
                "confirmed_at": mock_model_update.call_args[1]["data"]["confirmed_at"],
            },
        )
        
        # Verify audit log was created for unconfirmation
        mock_audit_create.assert_called_once()
        audit_call_args = mock_audit_create.call_args
        assert audit_call_args[1]["metadata"]["action"] == "unconfirmed"
        
        assert result == remittance


@pytest.mark.django_db
class TestSyncRemittance:
    """Test sync_remittance service method."""

    @patch("apps.remittance.services.RemittanceService._calculate_due_amount")
    @patch("apps.remittance.services.RemittanceService._calculate_paid_amount")
    @patch("apps.remittance.services.RemittanceService.update_remittance")
    def test_sync_remittance_both_calculations(
        self, mock_update, mock_calc_paid, mock_calc_due
    ):
        """Test sync_remittance with both due and paid amount calculations."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        mock_calc_due.return_value = Decimal("500.00")
        mock_calc_paid.return_value = Decimal("300.00")
        mock_update.return_value = remittance

        result = RemittanceService.sync_remittance(
            workspace_team=workspace_team,
            calc_due_amt=True,
            calc_paid_amt=True,
        )

        mock_calc_due.assert_called_once_with(workspace_team=workspace_team)
        mock_calc_paid.assert_called_once_with(workspace_team=workspace_team)
        mock_update.assert_called_once_with(remittance=remittance)
        assert result == remittance

    @patch("apps.remittance.services.RemittanceService._calculate_due_amount")
    @patch("apps.remittance.services.RemittanceService._calculate_paid_amount")
    @patch("apps.remittance.services.RemittanceService.update_remittance")
    def test_sync_remittance_only_due_calculation(
        self, mock_update, mock_calc_paid, mock_calc_due
    ):
        """Test sync_remittance with only due amount calculation."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)
        
        mock_calc_due.return_value = Decimal("500.00")
        mock_update.return_value = remittance

        result = RemittanceService.sync_remittance(
            workspace_team=workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

        mock_calc_due.assert_called_once_with(workspace_team=workspace_team)
        mock_calc_paid.assert_not_called()
        mock_update.assert_called_once_with(remittance=remittance)
        assert result == remittance

    @patch("apps.remittance.services.RemittanceService._calculate_due_amount")
    @patch("apps.remittance.services.RemittanceService._calculate_paid_amount")
    @patch("apps.remittance.services.RemittanceService.update_remittance")
    def test_sync_remittance_no_calculations(
        self, mock_update, mock_calc_paid, mock_calc_due
    ):
        """Test sync_remittance with no calculations (should not update)."""
        workspace_team = WorkspaceTeamFactory()
        remittance = Remittance.objects.get(workspace_team=workspace_team)

        result = RemittanceService.sync_remittance(
            workspace_team=workspace_team,
            calc_due_amt=False,
            calc_paid_amt=False,
        )

        mock_calc_due.assert_not_called()
        mock_calc_paid.assert_not_called()
        mock_update.assert_not_called()
        assert result == remittance


@pytest.mark.django_db
class TestRemittanceServicesIntegration:
    """Integration tests for remittance services."""

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_calculate_and_update_remittance_integration(self, mock_get_entries):
        """Test the full flow of calculating due amount and updating remittance."""
        # Setup
        mock_get_entries.side_effect = [
            Decimal("2000.00"),  # Income total
            Decimal("500.00"),  # Disbursement total
            Decimal("300.00"),  # Paid amount
        ]

        workspace_team = WorkspaceTeamFactory()
        workspace_team.custom_remittance_rate = 20  # 20%
        workspace_team.save()

        # Get the signal-created remittance
        remittance = Remittance.objects.get(workspace_team=workspace_team)

        # Calculate due amount
        due_amount = RemittanceService._calculate_due_amount(workspace_team=workspace_team)
        assert due_amount == Decimal("300.00")  # (2000 - 500) * 0.20

        # Calculate paid amount
        paid_amount = RemittanceService._calculate_paid_amount(workspace_team=workspace_team)
        assert paid_amount == Decimal("300.00")

        # Update remittance with calculated values
        remittance.due_amount = due_amount
        remittance.paid_amount = paid_amount
        remittance.save()

        # Update remittance status
        RemittanceService.update_remittance(remittance=remittance)

        # Verify the remittance was updated correctly
        remittance.refresh_from_db()
        assert remittance.status == RemittanceStatus.PAID  # 300.00 = 300.00
        assert remittance.is_overpaid is False