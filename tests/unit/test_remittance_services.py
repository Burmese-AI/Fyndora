"""
Unit tests for Remittance services.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch
from django.core.exceptions import PermissionDenied, ValidationError

from apps.remittance import services
from apps.remittance.models import Remittance
from apps.remittance.constants import RemittanceStatus
from apps.entries.constants import EntryType, EntryStatus
from tests.factories import (
    RemittanceFactory,
    PendingRemittanceFactory,
    PartiallyPaidRemittanceFactory,
    PaidRemittanceFactory,
    WorkspaceTeamFactory,
    WorkspaceFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
    EntryFactory,
    IncomeEntryFactory,
)


@pytest.mark.django_db
class TestRemittanceConfirmPayment:
    """Test remittance_confirm_payment service."""

    def setup_method(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(user=self.user)
        # Create workspace in the same organization as the member
        workspace = WorkspaceFactory(organization=self.member.organization)
        workspace_team = WorkspaceTeamFactory(workspace=workspace)
        self.remittance = PaidRemittanceFactory(
            workspace_team=workspace_team, confirmed_by=None, confirmed_at=None
        )

    def test_confirm_payment_success(self):
        """Test successful payment confirmation."""
        with patch.object(self.user, "has_perm", return_value=True):
            result = services.remittance_confirm_payment(
                remittance=self.remittance, user=self.user
            )

        assert result.confirmed_by == self.member
        assert result.confirmed_at is not None

    def test_confirm_payment_permission_denied(self):
        """Test confirmation fails without permission."""
        with patch.object(self.user, "has_perm", return_value=False):
            with pytest.raises(PermissionDenied) as exc_info:
                services.remittance_confirm_payment(
                    remittance=self.remittance, user=self.user
                )

        assert "You do not have permission to confirm" in str(exc_info.value)

    def test_confirm_payment_not_fully_paid(self):
        """Test confirmation fails when not fully paid."""
        partial_remittance = PartiallyPaidRemittanceFactory()

        with patch.object(self.user, "has_perm", return_value=True):
            with pytest.raises(ValidationError) as exc_info:
                services.remittance_confirm_payment(
                    remittance=partial_remittance, user=self.user
                )

        assert "due amount has not been fully paid" in str(exc_info.value)


@pytest.mark.django_db
class TestRemittanceRecordPayment:
    """Test remittance_record_payment service."""

    def setup_method(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(user=self.user)
        self.remittance = PendingRemittanceFactory(
            due_amount=Decimal("1000.00"), paid_amount=Decimal("0.00")
        )

    def test_record_payment_success(self):
        """Test successful payment recording."""
        with patch.object(self.user, "has_perm", return_value=True):
            result = services.remittance_record_payment(
                remittance=self.remittance, user=self.user, amount=Decimal("500.00")
            )

        assert result.paid_amount == Decimal("500.00")
        assert result.status == RemittanceStatus.PARTIAL

    def test_record_payment_full_amount(self):
        """Test recording full payment amount."""
        with patch.object(self.user, "has_perm", return_value=True):
            result = services.remittance_record_payment(
                remittance=self.remittance, user=self.user, amount=Decimal("1000.00")
            )

        assert result.paid_amount == Decimal("1000.00")
        assert result.status == RemittanceStatus.PAID

    def test_record_payment_permission_denied(self):
        """Test payment recording fails without permission."""
        with patch.object(self.user, "has_perm", return_value=False):
            with pytest.raises(PermissionDenied) as exc_info:
                services.remittance_record_payment(
                    remittance=self.remittance,
                    user=self.user,
                    amount=Decimal("500.00"),
                )

        assert "You do not have permission to record a payment" in str(exc_info.value)

    def test_record_payment_already_paid(self):
        """Test payment recording fails for already paid remittance."""
        paid_remittance = PaidRemittanceFactory()

        with patch.object(self.user, "has_perm", return_value=True):
            with pytest.raises(ValidationError) as exc_info:
                services.remittance_record_payment(
                    remittance=paid_remittance,
                    user=self.user,
                    amount=Decimal("100.00"),
                )

        assert "Cannot record a payment for a remittance with status" in str(
            exc_info.value
        )

    def test_record_payment_exceeds_due_amount(self):
        """Test payment recording fails when exceeding due amount."""
        with patch.object(self.user, "has_perm", return_value=True):
            with pytest.raises(ValidationError) as exc_info:
                services.remittance_record_payment(
                    remittance=self.remittance,
                    user=self.user,
                    amount=Decimal("1500.00"),  # Exceeds due amount of 1000
                )

        assert "Payment of 1500.00 exceeds the remaining due amount" in str(
            exc_info.value
        )

    def test_record_payment_multiple_payments(self):
        """Test multiple payment recordings."""
        with patch.object(self.user, "has_perm", return_value=True):
            # First payment
            result1 = services.remittance_record_payment(
                remittance=self.remittance, user=self.user, amount=Decimal("300.00")
            )
            assert result1.paid_amount == Decimal("300.00")
            assert result1.status == RemittanceStatus.PARTIAL

            # Second payment
            result2 = services.remittance_record_payment(
                remittance=self.remittance, user=self.user, amount=Decimal("700.00")
            )
            assert result2.paid_amount == Decimal("1000.00")
            assert result2.status == RemittanceStatus.PAID


@pytest.mark.django_db
class TestRemittanceCreateOrUpdateFromIncomeEntry:
    """Test remittance_create_or_update_from_income_entry service."""

    def setup_method(self):
        """Set up test data."""
        self.workspace = WorkspaceFactory(remittance_rate=Decimal("10.00"))
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, custom_remittance_rate=None
        )

    def test_create_remittance_from_income_entry(self):
        """Test creating new remittance from income entry."""
        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            amount=Decimal("1000.00"),
            entry_type=EntryType.INCOME,
        )

        result = services.remittance_create_or_update_from_income_entry(entry=entry)

        assert result is not None
        assert isinstance(result, Remittance)
        assert result.workspace_team == self.workspace_team
        assert result.due_amount == Decimal("100.00")  # 10% of 1000
        assert result.status == RemittanceStatus.PENDING

    def test_update_existing_remittance_from_income_entry(self):
        """Test updating existing remittance from income entry."""
        # Create existing remittance
        existing_remittance = PendingRemittanceFactory(
            workspace_team=self.workspace_team, due_amount=Decimal("50.00")
        )

        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            amount=Decimal("500.00"),
            entry_type=EntryType.INCOME,
        )

        result = services.remittance_create_or_update_from_income_entry(entry=entry)

        assert result.remittance_id == existing_remittance.remittance_id
        assert result.due_amount == Decimal("100.00")  # 50 + (10% of 500)

    def test_custom_remittance_rate_used(self):
        """Test custom remittance rate is used when available."""
        self.workspace_team.custom_remittance_rate = Decimal("15.00")
        self.workspace_team.save()

        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            amount=Decimal("1000.00"),
            entry_type=EntryType.INCOME,
        )

        result = services.remittance_create_or_update_from_income_entry(entry=entry)

        assert result.due_amount == Decimal("150.00")  # 15% of 1000

    def test_non_income_entry_returns_none(self):
        """Test non-income entry returns None."""
        entry = EntryFactory(
            workspace_team=self.workspace_team, entry_type=EntryType.DISBURSEMENT
        )

        result = services.remittance_create_or_update_from_income_entry(entry=entry)

        assert result is None

    def test_no_workspace_team_returns_none(self):
        """Test entry without workspace_team returns None."""
        entry = IncomeEntryFactory(workspace_team=None)

        result = services.remittance_create_or_update_from_income_entry(entry=entry)

        assert result is None

    def test_no_remittance_rate_returns_none(self):
        """Test workspace team without workspace returns None."""
        # Create an entry with a workspace team that has no workspace
        entry = IncomeEntryFactory(workspace_team=None, amount=Decimal("1000.00"))

        result = services.remittance_create_or_update_from_income_entry(entry=entry)

        assert result is None


@pytest.mark.django_db
class TestRemittanceCreate:
    """Test remittance_create service."""

    def setup_method(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(user=self.user)
        self.workspace_team = WorkspaceTeamFactory()

    def test_create_remittance_success(self):
        """Test successful remittance creation."""
        with patch.object(self.user, "has_perm", return_value=True):
            result = services.remittance_create(
                user=self.user,
                workspace_team=self.workspace_team,
                due_amount=Decimal("1000.00"),
            )

        assert isinstance(result, Remittance)
        assert result.workspace_team == self.workspace_team
        assert result.due_amount == Decimal("1000.00")
        assert result.status == RemittanceStatus.PENDING

    def test_create_remittance_permission_denied(self):
        """Test remittance creation fails without permission."""
        with patch.object(self.user, "has_perm", return_value=False):
            with pytest.raises(PermissionDenied) as exc_info:
                services.remittance_create(
                    user=self.user,
                    workspace_team=self.workspace_team,
                    due_amount=Decimal("1000.00"),
                )

        assert "You do not have permission to create a remittance" in str(
            exc_info.value
        )

    def test_create_remittance_invalid_amount(self):
        """Test remittance creation fails with invalid amount."""
        with patch.object(self.user, "has_perm", return_value=True):
            with pytest.raises(ValidationError) as exc_info:
                services.remittance_create(
                    user=self.user,
                    workspace_team=self.workspace_team,
                    due_amount=Decimal("-100.00"),
                )

        assert "Due amount must be positive" in str(exc_info.value)


@pytest.mark.django_db
class TestRemittanceCancel:
    """Test remittance_cancel service."""

    def setup_method(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(user=self.user)

    def test_cancel_remittance_success(self):
        """Test successful remittance cancellation."""
        remittance = PendingRemittanceFactory(paid_amount=Decimal("0.00"))

        with patch.object(self.user, "has_perm", return_value=True):
            result = services.remittance_cancel(remittance=remittance, user=self.user)

        assert result.status == RemittanceStatus.CANCELED

    def test_cancel_remittance_permission_denied(self):
        """Test cancellation fails without permission."""
        remittance = PendingRemittanceFactory()

        with patch.object(self.user, "has_perm", return_value=False):
            with pytest.raises(PermissionDenied) as exc_info:
                services.remittance_cancel(remittance=remittance, user=self.user)

        assert "You do not have permission to cancel" in str(exc_info.value)

    def test_cancel_remittance_with_payments(self):
        """Test cancellation fails when payments exist."""
        remittance = PartiallyPaidRemittanceFactory()

        with patch.object(self.user, "has_perm", return_value=True):
            with pytest.raises(ValidationError) as exc_info:
                services.remittance_cancel(remittance=remittance, user=self.user)

        assert "Cannot cancel a remittance that has payments recorded" in str(
            exc_info.value
        )

    def test_cancel_already_canceled_remittance(self):
        """Test canceling already canceled remittance."""
        remittance = RemittanceFactory(
            status=RemittanceStatus.CANCELED, paid_amount=Decimal("0.00")
        )

        with patch.object(self.user, "has_perm", return_value=True):
            result = services.remittance_cancel(remittance=remittance, user=self.user)

        assert result.status == RemittanceStatus.CANCELED


@pytest.mark.django_db
class TestUpdateRemittanceBasedOnEntryStatusChange:
    """Test update_remittance_based_on_entry_status_change service."""

    def test_update_due_amount(self):
        """Test updating due amount."""
        remittance = RemittanceFactory(
            due_amount=Decimal("500.00"), paid_amount=Decimal("200.00")
        )

        services.update_remittance_based_on_entry_status_change(
            remittance=remittance, due_amount=Decimal("800.00")
        )

        remittance.refresh_from_db()
        assert remittance.due_amount == Decimal("800.00")
        assert remittance.paid_amount == Decimal("200.00")  # Unchanged

    def test_update_paid_amount(self):
        """Test updating paid amount."""
        remittance = RemittanceFactory(
            due_amount=Decimal("1000.00"), paid_amount=Decimal("300.00")
        )

        services.update_remittance_based_on_entry_status_change(
            remittance=remittance, paid_amount=Decimal("600.00")
        )

        remittance.refresh_from_db()
        assert remittance.due_amount == Decimal("1000.00")  # Unchanged
        assert remittance.paid_amount == Decimal("600.00")

    def test_update_both_amounts(self):
        """Test updating both due and paid amounts."""
        remittance = RemittanceFactory(
            due_amount=Decimal("500.00"), paid_amount=Decimal("200.00")
        )

        services.update_remittance_based_on_entry_status_change(
            remittance=remittance,
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("400.00"),
        )

        remittance.refresh_from_db()
        assert remittance.due_amount == Decimal("1000.00")
        assert remittance.paid_amount == Decimal("400.00")


@pytest.mark.django_db
class TestHandleRemittanceUpdate:
    """Test handle_remittance_update service."""

    def setup_method(self):
        """Set up test data."""
        self.workspace_team = WorkspaceTeamFactory(
            custom_remittance_rate=Decimal("10.00")
        )
        self.remittance = RemittanceFactory(workspace_team=self.workspace_team)

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_handle_update_due_amount(self, mock_get_total):
        """Test handling due amount update."""
        # Mock the entry totals
        mock_get_total.side_effect = [
            Decimal("2000.00"),  # income_total
            Decimal("500.00"),  # disbursement_total
        ]

        entry = IncomeEntryFactory(workspace_team=self.workspace_team)

        services.handle_remittance_update(updated_entry=entry, update_due_amount=True)

        # Verify get_total_amount_of_entries was called correctly
        assert mock_get_total.call_count == 2

        # Check the calls
        calls = mock_get_total.call_args_list
        assert calls[0][1]["entry_type"] == EntryType.INCOME
        assert calls[0][1]["entry_status"] == EntryStatus.APPROVED
        assert calls[1][1]["entry_type"] == EntryType.DISBURSEMENT
        assert calls[1][1]["entry_status"] == EntryStatus.APPROVED

    @patch("apps.remittance.services.get_total_amount_of_entries")
    def test_handle_update_paid_amount(self, mock_get_total):
        """Test handling paid amount update."""
        mock_get_total.return_value = Decimal("800.00")  # remittance_total

        entry = EntryFactory(
            workspace_team=self.workspace_team, entry_type=EntryType.REMITTANCE
        )

        services.handle_remittance_update(updated_entry=entry, update_due_amount=False)

        # Verify get_total_amount_of_entries was called for remittance entries
        mock_get_total.assert_called_once_with(
            entry_type=EntryType.REMITTANCE,
            entry_status=EntryStatus.APPROVED,
            workspace_team=self.workspace_team,
        )
