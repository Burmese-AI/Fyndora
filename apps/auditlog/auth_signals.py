"""
Authentication signal handlers for audit logging.
"""

import logging

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from apps.auditlog.constants import AuditActionType
from apps.auditlog.services import (
    audit_create_authentication_event,
    audit_create_security_event,
)

from .utils import safe_audit_log

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
@safe_audit_log
def log_user_login(sender, request, user, **kwargs):
    """Automatically log successful logins"""
    audit_create_authentication_event(
        user=user,
        action_type=AuditActionType.LOGIN_SUCCESS,
        metadata={"login_method": "session", "automatic_logging": True},
    )


@receiver(user_logged_out)
@safe_audit_log
def log_user_logout(sender, request, user, **kwargs):
    """Automatically log logouts"""
    audit_create_authentication_event(
        user=user,
        action_type=AuditActionType.LOGOUT,
        metadata={"logout_method": "user_initiated", "automatic_logging": True},
    )


@receiver(user_login_failed)
@safe_audit_log
def log_failed_login(sender, credentials, request, **kwargs):
    """Automatically log failed login attempts"""
    audit_create_security_event(
        user=None,
        action_type=AuditActionType.LOGIN_FAILED,
        metadata={
            "attempted_username": credentials.get("username", ""),
            "failure_reason": "invalid_credentials",
            "automatic_logging": True,
        },
    )
