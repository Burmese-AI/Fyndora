from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Invitation


@receiver(pre_save, sender=Invitation)
def handle_invitation_creation(sender, instance, **kwargs):
    """
    Deactivate old invitations before creating a new active invitation
    """

    # Only for new invitations
    # Note: 'not instance.pk' doesn't work due to UUID field. pk is generated before the instance is saved)
    if not Invitation.objects.filter(pk=instance.pk).exists():
        # Deactivate unused active invitations
        Invitation.objects.filter(
            email=instance.email,
            organization=instance.organization,
            is_used=False,
            is_active=True,
        ).update(is_active=False)


@receiver(post_save, sender=Invitation)
def send_invitation_email(sender, instance, created, **kwargs):
    """
    Send invitation email after successful creation
    """
    if created and instance.is_active:
        print(f"Sending invitation email to {instance.email}")
        # Example:
        # from django.core.mail import send_mail
        # send_mail(
        #     'Your Invitation',
        #     f'Here is your invitation link: /invitations/accept/{instance.token}',
        #     'noreply@example.com',
        #     [instance.email],
        #     fail_silently=False,
        # )
