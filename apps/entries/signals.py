from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Entry
from .constants import EntryType, EntryStatus

@receiver(pre_save, sender=Entry)
def keep_remittance_updated_with_entry(sender, instance, **kwargs):
    remittance = getattr(instance.workspace, "remittance", None)
    if not remittance:
        return

    # Check if instance.pk exists in Entry table
    entry = Entry.objects.filter(pk=instance.pk).first()

    # If not exists (created) and status is APPROVED
    # For income/disbursement entries, add the due_amount of remittance
    # For remittance entries, add the paid_amount of remittance
    if not entry:
        if instance.status == EntryStatus.APPROVED:
            if instance.entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT]:
                remittance.due_amount += instance.amount
            elif instance.entry_type == EntryType.REMITTANCE:
                remittance.paid_amount += instance.amount
            remittance.save()
    else:
        # Prevent logic from getting triggered even though status doesn't change
        if entry.status == instance.status:
            return

        # If status is changed from something to APPROVED
        # For income/disbursement entries, add the due_amount of remittance
        # For remittance entries, add the paid_amount of remittance
        if instance.status == EntryStatus.APPROVED:
            if instance.entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT]:
                remittance.due_amount += instance.amount
            elif instance.entry_type == EntryType.REMITTANCE:
                remittance.paid_amount += instance.amount

        # If status is changed from APPROVED to something else
        # For income/disbursement entries, subtract the due_amount of remittance
        # For remittance entries, subtract the paid_amount of remittance
        elif entry.status == EntryStatus.APPROVED:
            if instance.entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT]:
                remittance.due_amount -= instance.amount
            elif instance.entry_type == EntryType.REMITTANCE:
                remittance.paid_amount -= instance.amount
                
        #TODO: What's left
        #Update Remittance Status based on the comparison of due_amount and paid_amount
        #Refactor these using selectors and services

        remittance.save()