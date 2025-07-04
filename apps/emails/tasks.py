import logging

import yagmail
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger("emails")


@shared_task
def send_email_task(to, subject, contents):
    """
    A Celery task to send an email using one of the configured Gmail accounts, rotating between them.
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
        # The key doesn't exist, so `incr` fails. We initialize it to 0.
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
    except Exception:
        logger.exception(f"Failed to send email to {to} from {gmail_user}.")
