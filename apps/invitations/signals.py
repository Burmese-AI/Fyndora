from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.emails.services import send_invitation_email as send_email

from .models import Invitation
from .selectors import invitation_exists
from .services import deactivate_all_unused_active_invitations


@receiver(pre_save, sender=Invitation)
def handle_invitation_creation(sender, instance, **kwargs):
    """
    Deactivates previous unused invitations for the same email and organization
    before saving a new invitation.
    """
    # Only apply this logic for new invitations
    if not invitation_exists(instance.pk):
        deactivate_all_unused_active_invitations(
            email=instance.email, organization=instance.organization
        )


@receiver(post_save, sender=Invitation)
def send_invitation_email(sender, instance, created, **kwargs):
    """
    Send invitation email after successful creation
    """
    if created and instance.is_active:
        send_email(instance)
