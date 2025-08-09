import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from .tasks import send_email_task

logger = logging.getLogger("emails")


def send_signup_confirmation_email(user):
    """
    Sends a signup confirmation email to the user.
    """
    send_email_task.delay(
        to=user.email,
        subject="Confirm your email address",
        contents=f"Please confirm your email address by clicking this link: {user.get_confirmation_url()}",
    )


def send_password_reset_email(user):
    """
    Sends a password reset email to the user.
    """
    send_email_task.delay(
        to=user.email,
        subject="Reset your password",
        contents=f"Please reset your password by clicking this link: {user.get_password_reset_url()}",
    )


def send_invitation_email(invitation):
    """
    Sends an invitation email to the invited user.
    """
    # Determine the domain and protocol for the invitation URL
    # Priority: DEBUG setting for development, then Sites framework, then ALLOWED_HOSTS
    if getattr(settings, "DEBUG", False):
        # In development, use localhost with port 8000
        domain = "localhost:8000"
        protocol = "http"
    else:
        # In production, try to get from Sites framework
        try:
            current_site = Site.objects.get_current()
            domain = current_site.domain
            # Use HTTPS in production, HTTP for localhost/development
            protocol = (
                "https"
                if domain != "localhost" and not domain.startswith("127.0.0.1")
                else "http"
            )
        except (Site.DoesNotExist, Exception):
            # Fallback to ALLOWED_HOSTS
            allowed_hosts = getattr(settings, "ALLOWED_HOSTS", ["localhost"])
            domain = allowed_hosts[0] if allowed_hosts else "localhost"
            protocol = (
                "https"
                if domain != "localhost" and not domain.startswith("127.0.0.1")
                else "http"
            )

    # Build the full acceptance URL
    acceptance_path = invitation.get_acceptance_url()
    acceptance_url = f"{protocol}://{domain}{acceptance_path}"

    # Prepare context for template rendering
    context = {
        "invitation": invitation,
        "organization": invitation.organization,
        "invited_by": invitation.invited_by,
        "acceptance_url": acceptance_url,
    }

    # Render subject
    subject = render_to_string("account/email/invitation_subject.txt", context)
    subject = "".join(subject.splitlines())  # Remove newlines from subject

    # Try to render HTML template first, fallback to text
    try:
        contents = render_to_string("account/email/invitation_message.html", context)
    except TemplateDoesNotExist:
        try:
            contents = render_to_string("account/email/invitation_message.txt", context)
        except TemplateDoesNotExist:
            logger.error(
                f"No invitation email templates found for invitation {invitation.pk}"
            )
            return

    # Send the email asynchronously
    send_email_task.delay(
        to=invitation.email,
        subject=subject,
        contents=contents,
    )

    logger.info(
        f"Invitation email queued for {invitation.email} to join {invitation.organization.title}"
    )
