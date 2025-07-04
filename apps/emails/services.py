import logging

import yagmail
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger("emails")


def send_email(to, subject, contents):
    """
    Sends an email using one of the configured Gmail accounts, rotating between them.
    Logs the outcome using Django's logging framework.
    """
    accounts = settings.GMAIL_ACCOUNTS
    if not accounts:
        logger.critical(
            "CRITICAL: No Gmail accounts are configured in settings.GMAIL_ACCOUNTS."
        )
        raise ImproperlyConfigured(
            "No Gmail accounts configured in settings.GMAIL_ACCOUNTS"
        )

    # Atomically increment the account index. `incr` is atomic and avoids race conditions.
    try:
        account_index = cache.incr("last_gmail_account_index")
    except ValueError:
        cache.set("last_gmail_account_index", 0)
        account_index = 0

    # Round-robin selection
    selected_account = accounts[account_index % len(accounts)]
    gmail_user = selected_account["user"]
    oauth2_file = selected_account["oauth2_file"]

    try:
        yag = yagmail.SMTP(gmail_user, oauth2_file=oauth2_file)
        yag.send(
            to=to,
            subject=subject,
            contents=contents,
        )
        logger.info(f"Email sent successfully to {to} from {gmail_user}.")
        return True
    except Exception:
        logger.exception(f"Failed to send email to {to} from {gmail_user}.")
        return False


def send_signup_confirmation_email(user):
    """
    Sends a signup confirmation email to the user.
    """
    subject = "Welcome to Fyndora! Please confirm your email."
    contents = f"Hi {user.username},\n\nThanks for signing up!"
    return send_email(to=user.email, subject=subject, contents=contents)


def send_password_reset_email(user):
    """
    Sends a password reset email to the user.
    """
    subject = "Password Reset for your Fyndora account."
    contents = f"Hi {user.username},\n\nClick the link below to reset your password."
    return send_email(to=user.email, subject=subject, contents=contents)
