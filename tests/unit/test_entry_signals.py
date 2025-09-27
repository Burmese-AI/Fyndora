"""
Unit tests for Entry signals.

Tests the signal handlers that manage remittance updates when entries are created, updated, or deleted.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.entries.signals import (
    keep_remittance_updated_with_entry,
    revert_remittance_on_entry_delete,
)
from apps.remittance.services import RemittanceService
from tests.factories import (
    EntryFactory,
    IncomeEntryFactory,
    WorkspaceTeamFactory,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestKeepRemittanceUpdatedWithEntry:
    """Test the keep_remittance_updated_with_entry signal handler."""

    def setup_method(self):
        """Set up test data."""
        self.workspace_team = WorkspaceTeamFactory()
        self.remittance = self.workspace_team.remittance

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_income_entry_triggers_due_amount_calculation(self, mock_sync_remittance):
        """Test that income entry triggers due amount calculation."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually
        keep_remittance_updated_with_entry(sender=Entry, instance=entry, created=True)

        # Verify sync_remittance was called with correct parameters
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_disbursement_entry_triggers_due_amount_calculation(self, mock_sync_remittance):
        """Test that disbursement entry triggers due amount calculation."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.DISBURSEMENT,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually
        keep_remittance_updated_with_entry(sender=Entry, instance=entry, created=True)

        # Verify sync_remittance was called with correct parameters
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_remittance_entry_triggers_paid_amount_calculation(self, mock_sync_remittance):
        """Test that remittance entry triggers paid amount calculation."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.REMITTANCE,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually
        keep_remittance_updated_with_entry(sender=Entry, instance=entry, created=True)

        # Verify sync_remittance was called with correct parameters
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=False,
            calc_paid_amt=True,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_workspace_expense_entry_does_not_trigger_remittance_update(
        self, mock_sync_remittance
    ):
        """Test that workspace expense entry does not trigger remittance update."""
        entry = EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Trigger the signal manually
        keep_remittance_updated_with_entry(sender=Entry, instance=entry, created=True)

        # Verify remittance was not updated
        mock_sync_remittance.assert_not_called()

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_organization_expense_entry_does_not_trigger_remittance_update(
        self, mock_sync_remittance
    ):
        """Test that organization expense entry does not trigger remittance update."""
        entry = EntryFactory(
            entry_type=EntryType.ORG_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Trigger the signal manually
        keep_remittance_updated_with_entry(sender=Entry, instance=entry, created=True)

        # Verify remittance was not updated
        mock_sync_remittance.assert_not_called()

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_entry_update_triggers_remittance_calculation(self, mock_sync_remittance):
        """Test that entry update (not creation) also triggers remittance calculation."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Update the entry
        entry.status = EntryStatus.APPROVED
        entry.save()

        # Clear calls from the save operation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually for update
        keep_remittance_updated_with_entry(sender=Entry, instance=entry, created=False)

        # Verify sync_remittance was called with correct parameters
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_multiple_entry_types_in_same_workspace_team(self, mock_sync_remittance):
        """Test handling multiple entry types in the same workspace team."""
        # Create income entry without triggering signals
        income_entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Create remittance entry without triggering signals
        remittance_entry = EntryFactory(
            entry_type=EntryType.REMITTANCE,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger signals for both entries
        keep_remittance_updated_with_entry(
            sender=Entry, instance=income_entry, created=True
        )

        keep_remittance_updated_with_entry(
            sender=Entry, instance=remittance_entry, created=True
        )

        # Verify sync_remittance was called twice with correct parameters
        assert mock_sync_remittance.call_count == 2
        
        # First call for income entry
        mock_sync_remittance.assert_any_call(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )
        
        # Second call for remittance entry
        mock_sync_remittance.assert_any_call(
            workspace_team=self.workspace_team,
            calc_due_amt=False,
            calc_paid_amt=True,
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestRevertRemittanceOnEntryDelete:
    """Test the revert_remittance_on_entry_delete signal handler."""

    def setup_method(self):
        """Set up test data."""
        self.workspace_team = WorkspaceTeamFactory()
        self.remittance = self.workspace_team.remittance

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_approved_income_entry_deletion_triggers_due_amount_recalculation(
        self, mock_sync_remittance
    ):
        """Test that deleting approved income entry triggers due amount recalculation."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually
        revert_remittance_on_entry_delete(sender=Entry, instance=entry)

        # Verify sync_remittance was called with correct parameters
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_approved_disbursement_entry_deletion_triggers_due_amount_recalculation(
        self, mock_sync_remittance
    ):
        """Test that deleting approved disbursement entry triggers due amount recalculation."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.DISBURSEMENT,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually
        revert_remittance_on_entry_delete(sender=Entry, instance=entry)

        # Verify sync_remittance was called with correct parameters
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_approved_remittance_entry_deletion_triggers_paid_amount_recalculation(
        self, mock_sync_remittance
    ):
        """Test that deleting approved remittance entry triggers paid amount recalculation."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.REMITTANCE,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually
        revert_remittance_on_entry_delete(sender=Entry, instance=entry)

        # Verify sync_remittance was called with correct parameters
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=False,
            calc_paid_amt=True,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_pending_entry_deletion_does_not_trigger_remittance_update(
        self, mock_sync_remittance
    ):
        """Test that deleting pending entry does not trigger remittance update."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually
        revert_remittance_on_entry_delete(sender=Entry, instance=entry)

        # Verify remittance was not updated
        mock_sync_remittance.assert_not_called()

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_rejected_entry_deletion_does_not_trigger_remittance_update(
        self, mock_sync_remittance
    ):
        """Test that deleting rejected entry does not trigger remittance update."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.REJECTED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger the signal manually
        revert_remittance_on_entry_delete(sender=Entry, instance=entry)

        # Verify remittance was not updated
        mock_sync_remittance.assert_not_called()

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_workspace_expense_entry_deletion_does_not_trigger_remittance_update(
        self, mock_sync_remittance
    ):
        """Test that deleting workspace expense entry does not trigger remittance update."""
        entry = EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Trigger the signal manually
        revert_remittance_on_entry_delete(sender=Entry, instance=entry)

        # Verify remittance was not updated
        mock_sync_remittance.assert_not_called()

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_organization_expense_entry_deletion_does_not_trigger_remittance_update(
        self, mock_sync_remittance
    ):
        """Test that deleting organization expense entry does not trigger remittance update."""
        entry = EntryFactory(
            entry_type=EntryType.ORG_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Trigger the signal manually
        revert_remittance_on_entry_delete(sender=Entry, instance=entry)

        # Verify remittance was not updated
        mock_sync_remittance.assert_not_called()

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_multiple_approved_entries_deletion(self, mock_sync_remittance):
        """Test deletion of multiple approved entries triggers appropriate recalculations."""
        # Create approved income entry without triggering signals
        income_entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Create approved remittance entry without triggering signals
        remittance_entry = EntryFactory(
            entry_type=EntryType.REMITTANCE,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Clear any calls from factory creation
        mock_sync_remittance.reset_mock()

        # Trigger signals for both entries
        revert_remittance_on_entry_delete(sender=Entry, instance=income_entry)
        revert_remittance_on_entry_delete(sender=Entry, instance=remittance_entry)

        # Verify sync_remittance was called twice with correct parameters
        assert mock_sync_remittance.call_count == 2
        
        # First call for income entry
        mock_sync_remittance.assert_any_call(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )
        
        # Second call for remittance entry
        mock_sync_remittance.assert_any_call(
            workspace_team=self.workspace_team,
            calc_due_amt=False,
            calc_paid_amt=True,
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestEntrySignalIntegration:
    """Integration tests for entry signals."""

    def setup_method(self):
        """Set up test data."""
        self.workspace_team = WorkspaceTeamFactory()
        self.remittance = self.workspace_team.remittance

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_signal_handlers_are_connected(self, mock_sync_remittance):
        """Test that signal handlers are properly connected to Entry model."""
        # Create an entry - this should trigger the post_save signal
        IncomeEntryFactory(
            workspace_team=self.workspace_team, status=EntryStatus.APPROVED
        )

        # Verify the signal was triggered
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_signal_handlers_with_entry_updates(self, mock_sync_remittance):
        """Test signal handlers work with entry updates."""
        # Create a pending entry
        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team, status=EntryStatus.PENDING
        )

        # Clear previous calls
        mock_sync_remittance.reset_mock()

        # Update entry to approved status
        entry.status = EntryStatus.APPROVED
        entry.save()

        # Verify the signal was triggered on update
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_signal_handlers_with_entry_deletion(self, mock_sync_remittance):
        """Test signal handlers work with entry deletion."""
        # Create an approved entry
        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team, status=EntryStatus.APPROVED
        )

        # Clear previous calls
        mock_sync_remittance.reset_mock()

        # Delete the entry
        entry.delete()

        # Verify the signal was triggered on deletion
        mock_sync_remittance.assert_called_once_with(
            workspace_team=self.workspace_team,
            calc_due_amt=True,
            calc_paid_amt=False,
        )

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_signal_handlers_with_different_entry_types(self, mock_sync_remittance):
        """Test signal handlers with different entry types."""
        # Test with income entry
        EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Test with disbursement entry
        EntryFactory(
            entry_type=EntryType.DISBURSEMENT,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Verify both entries triggered sync_remittance
        assert mock_sync_remittance.call_count == 2
        # Both should call with calc_due_amt=True, calc_paid_amt=False
        for call in mock_sync_remittance.call_args_list:
            args, kwargs = call
            assert kwargs['calc_due_amt'] == True
            assert kwargs['calc_paid_amt'] == False

    @patch("apps.entries.signals.RemittanceService.sync_remittance")
    def test_signal_handlers_with_expense_entries(self, mock_sync_remittance):
        """Test that expense entries do not trigger remittance updates."""
        # Create workspace expense entry
        EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Create organization expense entry
        EntryFactory(
            entry_type=EntryType.ORG_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED,
        )

        # Verify no remittance updates were triggered
        mock_sync_remittance.assert_not_called()