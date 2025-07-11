from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from .models import Entry
from .constants import EntryType, EntryStatus
from apps.remittance.services import update_remittance_based_on_entry_status_change, revert_approved_effect

@receiver(pre_save, sender=Entry)
def keep_remittance_updated_with_entry(sender, instance, **kwargs):
    if instance.entry_type not in [
        EntryType.INCOME, EntryType.REMITTANCE
    ]:
        return

    old_entry = Entry.objects.filter(pk=instance.pk).first()
    update_remittance_based_on_entry_status_change(old_entry, instance)
    
@receiver(post_delete, sender=Entry)
def revert_remittance_on_entry_delete(sender, instance, **kwargs):
    if instance.status != EntryStatus.APPROVED:
        return

    if instance.entry_type not in [EntryType.INCOME, EntryType.REMITTANCE]:
        return

    remittance = instance.workspace_team.remittance
    revert_approved_effect(instance, remittance)
    remittance.save()