from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import WorkspaceTeam
from apps.remittance.models import Remittance


@receiver(post_save, sender=WorkspaceTeam)
def create_remittance(sender, instance, created, **kwargs):
    """
    Create remittance object to track after creating workspace team
    """

    if created:
        remittance = Remittance.objects.create(workspace_team=instance)
        print(f"created {remittance}")
