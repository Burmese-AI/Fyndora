from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Entry
from .constants import EntryType, EntryStatus
from apps.remittance.services import (
    RemittanceService,
)


@receiver(post_save, sender=Entry)
def keep_remittance_updated_with_entry(sender, instance: Entry, created, **kwargs):
    # Prevent Remittance Process on Expense entry types
    if instance.entry_type not in [
        EntryType.INCOME,
        EntryType.DISBURSEMENT,
        EntryType.REMITTANCE,
    ]:
        return

    RemittanceService.sync_remittance(
        workspace_team=instance.workspace_team,
        calc_due_amt=instance.entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT],
        calc_paid_amt=instance.entry_type == EntryType.REMITTANCE,
    )


@receiver(post_delete, sender=Entry)
def revert_remittance_on_entry_delete(sender, instance: Entry, **kwargs):
    # Prevent Remittance Process on Expense entry types
    if instance.entry_type not in [
        EntryType.INCOME,
        EntryType.DISBURSEMENT,
        EntryType.REMITTANCE,
    ]:
        return

    # Only act if entry was APPROVED before deletion
    if instance.status != EntryStatus.APPROVED:
        return

    RemittanceService.sync_remittance(
        workspace_team=instance.workspace_team,
        calc_due_amt=instance.entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT],
        calc_paid_amt=instance.entry_type == EntryType.REMITTANCE,
    )
