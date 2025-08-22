from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Entry
from .constants import EntryType, EntryStatus
from apps.remittance.services import (
    handle_remittance_update,
)


@receiver(post_save, sender=Entry)
def keep_remittance_updated_with_entry(sender, instance, created, **kwargs):
    # Only handle relevant entry types
    if instance.entry_type not in [
        EntryType.INCOME,
        EntryType.DISBURSEMENT,
        EntryType.REMITTANCE,
    ]:
        return

    # print("About to update remittance")
    handle_remittance_update(
        updated_entry=instance,
        update_due_amount=instance.entry_type
        in [EntryType.INCOME, EntryType.DISBURSEMENT],
    )


@receiver(post_delete, sender=Entry)
def revert_remittance_on_entry_delete(sender, instance, **kwargs):
    # Only act if entry was APPROVED before deletion
    if instance.status != EntryStatus.APPROVED:
        return

    # Only handle relevant entry types
    if instance.entry_type not in [
        EntryType.INCOME,
        EntryType.DISBURSEMENT,
        EntryType.REMITTANCE,
    ]:
        return

    print("Recalculating remittance after entry deletion")
    handle_remittance_update(
        updated_entry=instance,
        update_due_amount=instance.entry_type
        in [EntryType.INCOME, EntryType.DISBURSEMENT],
    )
