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
    Includes fallback mechanism to skip problematic accounts.
    Logs the outcome using Django's logging framework.
    """
    accounts = getattr(settings, "GMAIL_ACCOUNTS")
    if not accounts:
        logger.critical(
            "CRITICAL: No Gmail accounts are configured in settings.GMAIL_ACCOUNTS."
        )
        raise ImproperlyConfigured(
            "No Gmail accounts configured in settings.GMAIL_ACCOUNTS"
        )

    # Try up to len(accounts) times to find a working account
    max_attempts = len(accounts)
    last_exception = None

    for attempt in range(max_attempts):
        # Atomically increment a counter to get the next index.
        try:
            account_index = cache.incr("last_gmail_account_index")
        except ValueError:
            cache.set("last_gmail_account_index", 1)
            account_index = 1

        # Perform round-robin selection.
        selected_account_index = (account_index - 1) % len(accounts)
        selected_account = accounts[selected_account_index]
        gmail_user = selected_account.get("user")
        oauth2_file = selected_account.get("oauth2_file")

        try:
            yag = yagmail.SMTP(gmail_user, oauth2_file=oauth2_file)
            yag.send(
                to=to,
                subject=subject,
                contents=contents,
            )
            logger.info(f"Email sent successfully to {to} from {gmail_user}.")

            # Mark account as healthy in cache (optional)
            cache.set(
                f"gmail_account_healthy_{selected_account_index}", True, timeout=3600
            )
            return  # Success, exit the function

        except (ImportError, FileNotFoundError):
            # Re-raise critical errors that should not be silently handled
            raise
        except Exception as e:
            last_exception = e
            logger.warning(
                f"Failed to send email to {to} from {gmail_user} (attempt {attempt + 1}/{max_attempts}): {e}"
            )

            # Mark account as potentially unhealthy
            cache.set(
                f"gmail_account_healthy_{selected_account_index}", False, timeout=300
            )

            # If this is not the last attempt, continue to next account
            if attempt < max_attempts - 1:
                continue

    # If we get here, all accounts failed
    logger.error(
        f"Failed to send email to {to} after trying all {max_attempts} accounts."
    )
    if last_exception:
        raise last_exception
