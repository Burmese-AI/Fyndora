"""
Unit tests for Entry signals.

Tests the signal handlers that manage remittance updates when entries are created, updated, or deleted.
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.db.models.signals import post_delete, post_save
from django.test import TestCase

from apps.entries.constants import EntryStatus, EntryType
from apps.entries.models import Entry
from apps.entries.signals import (
    keep_remittance_updated_with_entry,
    revert_remittance_on_entry_delete,
)
from tests.factories import (
    EntryFactory,
    IncomeEntryFactory,
    DisbursementEntryFactory,
    RemittanceEntryFactory,
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

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_income_entry_triggers_due_amount_calculation(self, mock_update_remittance, mock_calculate_due):
        """Test that income entry triggers due amount calculation."""
        mock_calculate_due.return_value = Decimal("100.00")
        
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Clear any calls from factory creation
        mock_calculate_due.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually
        keep_remittance_updated_with_entry(
            sender=Entry,
            instance=entry,
            created=True
        )
        
        # Verify due amount was calculated and remittance was updated
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        assert self.remittance.due_amount == Decimal("100.00")
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_disbursement_entry_triggers_due_amount_calculation(self, mock_update_remittance, mock_calculate_due):
        """Test that disbursement entry triggers due amount calculation."""
        mock_calculate_due.return_value = Decimal("200.00")
        
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.DISBURSEMENT,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Clear any calls from factory creation
        mock_calculate_due.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually
        keep_remittance_updated_with_entry(
            sender=Entry,
            instance=entry,
            created=True
        )
        
        # Verify due amount was calculated and remittance was updated
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        assert self.remittance.due_amount == Decimal("200.00")
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    @patch('apps.entries.signals.calculate_paid_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_remittance_entry_triggers_paid_amount_calculation(self, mock_update_remittance, mock_calculate_paid):
        """Test that remittance entry triggers paid amount calculation."""
        mock_calculate_paid.return_value = Decimal("150.00")
        
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.REMITTANCE,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Clear any calls from factory creation
        mock_calculate_paid.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually
        keep_remittance_updated_with_entry(
            sender=Entry,
            instance=entry,
            created=True
        )
        
        # Verify paid amount was calculated and remittance was updated
        mock_calculate_paid.assert_called_once_with(workspace_team=self.workspace_team)
        assert self.remittance.paid_amount == Decimal("150.00")
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    @patch('apps.entries.signals.update_remittance')
    def test_workspace_expense_entry_does_not_trigger_remittance_update(self, mock_update_remittance):
        """Test that workspace expense entry does not trigger remittance update."""
        entry = EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Trigger the signal manually
        keep_remittance_updated_with_entry(
            sender=Entry,
            instance=entry,
            created=True
        )
        
        # Verify remittance was not updated
        mock_update_remittance.assert_not_called()

    @patch('apps.entries.signals.update_remittance')
    def test_organization_expense_entry_does_not_trigger_remittance_update(self, mock_update_remittance):
        """Test that organization expense entry does not trigger remittance update."""
        entry = EntryFactory(
            entry_type=EntryType.ORG_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Trigger the signal manually
        keep_remittance_updated_with_entry(
            sender=Entry,
            instance=entry,
            created=True
        )
        
        # Verify remittance was not updated
        mock_update_remittance.assert_not_called()

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_entry_update_triggers_remittance_calculation(self, mock_update_remittance, mock_calculate_due):
        """Test that entry update (not creation) also triggers remittance calculation."""
        mock_calculate_due.return_value = Decimal("300.00")
        
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING
        )
        
        # Clear any calls from factory creation
        mock_calculate_due.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Update the entry
        entry.status = EntryStatus.APPROVED
        entry.save()
        
        # Clear calls from the save operation
        mock_calculate_due.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually for update
        keep_remittance_updated_with_entry(
            sender=Entry,
            instance=entry,
            created=False
        )
        
        # Verify due amount was calculated and remittance was updated
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        assert self.remittance.due_amount == Decimal("300.00")
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.calculate_paid_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_multiple_entry_types_in_same_workspace_team(self, mock_update_remittance, mock_calculate_paid, mock_calculate_due):
        """Test handling multiple entry types in the same workspace team."""
        mock_calculate_due.return_value = Decimal("100.00")
        mock_calculate_paid.return_value = Decimal("50.00")
        
        # Create income entry without triggering signals
        income_entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Create remittance entry without triggering signals
        remittance_entry = EntryFactory(
            entry_type=EntryType.REMITTANCE,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Clear any calls from factory creation
        mock_calculate_due.reset_mock()
        mock_calculate_paid.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger signals for both entries
        keep_remittance_updated_with_entry(
            sender=Entry,
            instance=income_entry,
            created=True
        )
        
        keep_remittance_updated_with_entry(
            sender=Entry,
            instance=remittance_entry,
            created=True
        )
        
        # Verify both calculations were called
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        mock_calculate_paid.assert_called_once_with(workspace_team=self.workspace_team)
        
        # Verify remittance was updated twice
        assert mock_update_remittance.call_count == 2


@pytest.mark.unit
@pytest.mark.django_db
class TestRevertRemittanceOnEntryDelete:
    """Test the revert_remittance_on_entry_delete signal handler."""

    def setup_method(self):
        """Set up test data."""
        self.workspace_team = WorkspaceTeamFactory()
        self.remittance = self.workspace_team.remittance

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_approved_income_entry_deletion_triggers_due_amount_recalculation(self, mock_update_remittance, mock_calculate_due):
        """Test that deleting approved income entry triggers due amount recalculation."""
        mock_calculate_due.return_value = Decimal("50.00")
        
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Clear any calls from factory creation
        mock_calculate_due.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=entry
        )
        
        # Verify due amount was recalculated and remittance was updated
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        assert self.remittance.due_amount == Decimal("50.00")
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_approved_disbursement_entry_deletion_triggers_due_amount_recalculation(self, mock_update_remittance, mock_calculate_due):
        """Test that deleting approved disbursement entry triggers due amount recalculation."""
        mock_calculate_due.return_value = Decimal("75.00")
        
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.DISBURSEMENT,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Clear any calls from factory creation
        mock_calculate_due.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=entry
        )
        
        # Verify due amount was recalculated and remittance was updated
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        assert self.remittance.due_amount == Decimal("75.00")
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    @patch('apps.entries.signals.calculate_paid_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_approved_remittance_entry_deletion_triggers_paid_amount_recalculation(self, mock_update_remittance, mock_calculate_paid):
        """Test that deleting approved remittance entry triggers paid amount recalculation."""
        mock_calculate_paid.return_value = Decimal("25.00")
        
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.REMITTANCE,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Clear any calls from factory creation
        mock_calculate_paid.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=entry
        )
        
        # Verify paid amount was recalculated and remittance was updated
        mock_calculate_paid.assert_called_once_with(workspace_team=self.workspace_team)
        assert self.remittance.paid_amount == Decimal("25.00")
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    @patch('apps.entries.signals.update_remittance')
    def test_pending_entry_deletion_does_not_trigger_remittance_update(self, mock_update_remittance):
        """Test that deleting pending entry does not trigger remittance update."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING
        )
        
        # Clear any calls from factory creation
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=entry
        )
        
        # Verify remittance was not updated
        mock_update_remittance.assert_not_called()

    @patch('apps.entries.signals.update_remittance')
    def test_rejected_entry_deletion_does_not_trigger_remittance_update(self, mock_update_remittance):
        """Test that deleting rejected entry does not trigger remittance update."""
        # Create entry without triggering signals
        entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.REJECTED
        )
        
        # Clear any calls from factory creation
        mock_update_remittance.reset_mock()
        
        # Trigger the signal manually
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=entry
        )
        
        # Verify remittance was not updated
        mock_update_remittance.assert_not_called()

    @patch('apps.entries.signals.update_remittance')
    def test_workspace_expense_entry_deletion_does_not_trigger_remittance_update(self, mock_update_remittance):
        """Test that deleting workspace expense entry does not trigger remittance update."""
        entry = EntryFactory(
            entry_type=EntryType.WORKSPACE_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Trigger the signal manually
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=entry
        )
        
        # Verify remittance was not updated
        mock_update_remittance.assert_not_called()

    @patch('apps.entries.signals.update_remittance')
    def test_organization_expense_entry_deletion_does_not_trigger_remittance_update(self, mock_update_remittance):
        """Test that deleting organization expense entry does not trigger remittance update."""
        entry = EntryFactory(
            entry_type=EntryType.ORG_EXP,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Trigger the signal manually
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=entry
        )
        
        # Verify remittance was not updated
        mock_update_remittance.assert_not_called()

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.calculate_paid_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_multiple_approved_entries_deletion(self, mock_update_remittance, mock_calculate_paid, mock_calculate_due):
        """Test deletion of multiple approved entries triggers appropriate recalculations."""
        mock_calculate_due.return_value = Decimal("100.00")
        mock_calculate_paid.return_value = Decimal("50.00")
        
        # Create approved income entry without triggering signals
        income_entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Create approved remittance entry without triggering signals
        remittance_entry = EntryFactory(
            entry_type=EntryType.REMITTANCE,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Clear any calls from factory creation
        mock_calculate_due.reset_mock()
        mock_calculate_paid.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Trigger signals for both entries
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=income_entry
        )
        
        revert_remittance_on_entry_delete(
            sender=Entry,
            instance=remittance_entry
        )
        
        # Verify both calculations were called
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        mock_calculate_paid.assert_called_once_with(workspace_team=self.workspace_team)
        
        # Verify remittance was updated twice
        assert mock_update_remittance.call_count == 2


@pytest.mark.unit
@pytest.mark.django_db
class TestEntrySignalIntegration:
    """Integration tests for entry signals."""

    def setup_method(self):
        """Set up test data."""
        self.workspace_team = WorkspaceTeamFactory()
        self.remittance = self.workspace_team.remittance

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_signal_handlers_are_connected(self, mock_update_remittance, mock_calculate_due):
        """Test that signal handlers are properly connected to Entry model."""
        mock_calculate_due.return_value = Decimal("100.00")
        
        # Create an entry - this should trigger the post_save signal
        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Verify the signal was triggered
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_signal_handlers_with_entry_updates(self, mock_update_remittance, mock_calculate_due):
        """Test signal handlers work with entry updates."""
        mock_calculate_due.return_value = Decimal("150.00")
        
        # Create a pending entry
        entry = IncomeEntryFactory(
            workspace_team=self.workspace_team,
            status=EntryStatus.PENDING
        )
        
        # Clear previous calls
        mock_calculate_due.reset_mock()
        mock_update_remittance.reset_mock()
        
        # Update entry to approved status
        entry.status = EntryStatus.APPROVED
        entry.save()
        
        # Verify the signal was triggered on update
        mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)
        mock_update_remittance.assert_called_once_with(remittance=self.remittance)

    def test_signal_handlers_with_entry_deletion(self):
        """Test signal handlers work with entry deletion."""
        with patch('apps.entries.signals.calculate_due_amount') as mock_calculate_due:
            mock_calculate_due.return_value = Decimal("50.00")
            
            # Create an approved entry
            entry = IncomeEntryFactory(
                workspace_team=self.workspace_team,
                status=EntryStatus.APPROVED
            )
            
            # Clear previous calls
            mock_calculate_due.reset_mock()
            
            # Delete the entry
            entry.delete()
            
            # Verify the signal was triggered on deletion
            mock_calculate_due.assert_called_once_with(workspace_team=self.workspace_team)

    @patch('apps.entries.signals.calculate_due_amount')
    @patch('apps.entries.signals.update_remittance')
    def test_signal_handlers_with_different_entry_types(self, mock_update_remittance, mock_calculate_due):
        """Test signal handlers with different entry types."""
        mock_calculate_due.return_value = Decimal("100.00")
        
        # Test with income entry
        income_entry = EntryFactory(
            entry_type=EntryType.INCOME,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Test with disbursement entry
        disbursement_entry = EntryFactory(
            entry_type=EntryType.DISBURSEMENT,
            workspace_team=self.workspace_team,
            status=EntryStatus.APPROVED
        )
        
        # Verify both entries triggered due amount calculation
        assert mock_calculate_due.call_count == 2
        assert mock_update_remittance.call_count == 2

    def test_signal_handlers_with_expense_entries(self):
        """Test that expense entries do not trigger remittance updates."""
        with patch('apps.entries.signals.update_remittance') as mock_update_remittance:
            # Create workspace expense entry
            workspace_exp_entry = EntryFactory(
                entry_type=EntryType.WORKSPACE_EXP,
                workspace_team=self.workspace_team,
                status=EntryStatus.APPROVED
            )
            
            # Create organization expense entry
            org_exp_entry = EntryFactory(
                entry_type=EntryType.ORG_EXP,
                workspace_team=self.workspace_team,
                status=EntryStatus.APPROVED
            )
            
            # Verify no remittance updates were triggered
            mock_update_remittance.assert_not_called()
