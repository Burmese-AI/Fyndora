from django.core.signals import post_save
from django.dispatch import receiver
from .models import Entry

@receiver(post_save, sender=Entry)
def update_remittance(sender, instance, created, **kwargs):
    # If instance is created and status is already approved, 
    # For income/disbursement entries, add the due_amount of remittance
    # For remittance entries, add the paid_amount of remittance
    if created:
        print(f"created {instance}")
        return
    
    # If instance status is update from something to approved
    # For income/disbursement entries, add the due_amount of remittance
    # For remittance entries, add the paid_amount of remittance
    print(f"updated {instance}")
    # If instance status is update from approved to something else
    # For income/disbursement entries, subtract the due_amount of remittance
    # For remittance entries, subtract the paid_amount of remittance
    return
    