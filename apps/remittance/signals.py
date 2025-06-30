from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.entries.models import Entry
from apps.remittance.services import remittance_create_or_update_from_income_entry


@receiver(post_save, sender=Entry)
def calculate_remittance_on_income(sender, instance, created, **kwargs):
    """
    Signal handler to trigger remittance calculation when an income entry is submitted.
    """
    if created:
        remittance_create_or_update_from_income_entry(entry=instance)
