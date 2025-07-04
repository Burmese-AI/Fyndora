import logging

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
