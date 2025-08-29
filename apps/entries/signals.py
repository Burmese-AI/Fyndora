from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Entry
from .constants import EntryType, EntryStatus
from apps.remittance.services import (
    calculate_due_amount,
    calculate_paid_amount,
    update_remittance,
)


@receiver(post_save, sender=Entry)
def keep_remittance_updated_with_entry(sender, instance: Entry, created, **kwargs):
    
    workspace_team = instance.workspace_team
    remittance = workspace_team.remittance
    required_to_update = False
    
    # Recalc remittance due amount if entry is income or disbursement
    if instance.entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT]:
        remittance.due_amount = calculate_due_amount(workspace_team=workspace_team)
        required_to_update = True
    # Recalc remittance paid amount if entry is remittance
    if instance.entry_type == EntryType.REMITTANCE:
        remittance.paid_amount = calculate_paid_amount(workspace_team=workspace_team)
        required_to_update = True
    if required_to_update:
        update_remittance(remittance=remittance)



@receiver(post_delete, sender=Entry)
def revert_remittance_on_entry_delete(sender, instance: Entry, **kwargs):
    # Only act if entry was APPROVED before deletion
    if instance.status != EntryStatus.APPROVED:
        return
    
    workspace_team = instance.workspace_team
    remittance = workspace_team.remittance
    required_to_update = False

    # Recalc remittance due amount if entry is income or disbursement
    if instance.entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT]:
        remittance.due_amount = calculate_due_amount(workspace_team=workspace_team)
        required_to_update = True
    # Recalc remittance paid amount if entry is remittance
    if instance.entry_type == EntryType.REMITTANCE:
        remittance.paid_amount = calculate_paid_amount(workspace_team=workspace_team)
        required_to_update = True
    if required_to_update:
        update_remittance(remittance=remittance)

