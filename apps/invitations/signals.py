from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Invitation

@receiver(pre_save, sender=Invitation)
def handle_invitation_creation(sender, instance, **kwargs):
    """
    Deactivate old invitations and ensure new one is active
    """
    print(f">>> testing pre save {instance}")
    if not Invitation.objects.filter(pk=instance.pk).exists():  # Only for new invitations
        print(f">>> Handling invitation creation")
        # Deactivate old invitations (no save needed after update)
        Invitation.objects.filter(
            email=instance.email,
            organization=instance.organization,
            is_used=False,
            is_active=True
        ).update(is_active=False)
        
        # Ensure new invitation is active
        instance.is_active = True

@receiver(post_save, sender=Invitation)
def send_invitation_email(sender, instance, created, **kwargs):
    """
    Send invitation email after successful creation
    """
    if created and instance.is_active:
        # Actual email sending implementation would go here
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
        
print(">>> pre_save connected:", pre_save.receivers)