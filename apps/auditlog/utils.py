"""
Audit logging utilities and helpers for the Fyndora project.

This module provides convenient functions and mappings to help developers
choose the appropriate audit action types for different operations.
"""

import json
import logging
from functools import wraps

from .config import AuditConfig
from .constants import AuditActionType

logger = logging.getLogger(__name__)


class AuditActionMapper:
    """
    Helper class to map common operations to appropriate audit action types.
    """

    # Authentication mappings
    AUTH_ACTIONS = {
        "login_success": AuditActionType.LOGIN_SUCCESS,
        "login_failed": AuditActionType.LOGIN_FAILED,
        "logout": AuditActionType.LOGOUT,
        "password_changed": AuditActionType.PASSWORD_CHANGED,
        "password_reset_requested": AuditActionType.PASSWORD_RESET_REQUESTED,
        "password_reset_completed": AuditActionType.PASSWORD_RESET_COMPLETED,
    }

    # CRUD operation mappings
    CRUD_ACTIONS = {
        "user": {
            "create": AuditActionType.USER_CREATED,
            "update": AuditActionType.USER_UPDATED,
            "delete": AuditActionType.USER_DELETED,
        },
        "organization": {
            "create": AuditActionType.ORGANIZATION_CREATED,
            "update": AuditActionType.ORGANIZATION_UPDATED,
            "delete": AuditActionType.ORGANIZATION_DELETED,
        },
        "workspace": {
            "create": AuditActionType.WORKSPACE_CREATED,
            "update": AuditActionType.WORKSPACE_UPDATED,
            "delete": AuditActionType.WORKSPACE_DELETED,
        },
        "team": {
            "create": AuditActionType.TEAM_CREATED,
            "update": AuditActionType.TEAM_UPDATED,
            "delete": AuditActionType.TEAM_DELETED,
        },
        "entry": {
            "create": AuditActionType.ENTRY_CREATED,
            "update": AuditActionType.ENTRY_UPDATED,
            "delete": AuditActionType.ENTRY_DELETED,
        },
        "remittance": {
            "create": AuditActionType.REMITTANCE_CREATED,
            "update": AuditActionType.REMITTANCE_UPDATED,
            "delete": AuditActionType.REMITTANCE_DELETED,
        },
        "attachment": {
            "create": AuditActionType.ATTACHMENT_ADDED,
            "update": AuditActionType.ATTACHMENT_UPDATED,
            "delete": AuditActionType.ATTACHMENT_REMOVED,
        },
        "exchange_rate": {
            "create": AuditActionType.EXCHANGE_RATE_CREATED,
            "update": AuditActionType.EXCHANGE_RATE_UPDATED,
            "delete": AuditActionType.EXCHANGE_RATE_DELETED,
        },
    }

    # Status change mappings
    STATUS_ACTIONS = {
        "organization": {
            "active": AuditActionType.ORGANIZATION_ACTIVATED,
            "archived": AuditActionType.ORGANIZATION_ARCHIVED,
            "closed": AuditActionType.ORGANIZATION_CLOSED,
        },
        "workspace": {
            "active": AuditActionType.WORKSPACE_ACTIVATED,
            "archived": AuditActionType.WORKSPACE_ARCHIVED,
            "closed": AuditActionType.WORKSPACE_CLOSED,
        },
        "entry": {
            "pending": AuditActionType.ENTRY_SUBMITTED,
            "reviewed": AuditActionType.ENTRY_REVIEWED,
            "approved": AuditActionType.ENTRY_APPROVED,
            "rejected": AuditActionType.ENTRY_REJECTED,
        },
        "remittance": {
            "paid": AuditActionType.REMITTANCE_PAID,
            "partial": AuditActionType.REMITTANCE_PARTIALLY_PAID,
            "overdue": AuditActionType.REMITTANCE_OVERDUE,
            "canceled": AuditActionType.REMITTANCE_CANCELED,
        },
    }

    # Member management mappings
    MEMBER_ACTIONS = {
        "organization": {
            "add": AuditActionType.ORGANIZATION_MEMBER_ADDED,
            "remove": AuditActionType.ORGANIZATION_MEMBER_REMOVED,
            "role_change": AuditActionType.ORGANIZATION_MEMBER_ROLE_CHANGED,
            "update": AuditActionType.ORGANIZATION_MEMBER_UPDATED,
        },
        "team": {
            "add": AuditActionType.TEAM_MEMBER_ADDED,
            "remove": AuditActionType.TEAM_MEMBER_REMOVED,
            "role_change": AuditActionType.TEAM_MEMBER_ROLE_CHANGED,
        },
    }

    # File operation mappings
    FILE_ACTIONS = {
        "upload": AuditActionType.FILE_UPLOADED,
        "download": AuditActionType.FILE_DOWNLOADED,
        "delete": AuditActionType.FILE_DELETED,
    }

    # Invitation mappings
    INVITATION_ACTIONS = {
        "send": AuditActionType.INVITATION_SENT,
        "accept": AuditActionType.INVITATION_ACCEPTED,
        "decline": AuditActionType.INVITATION_DECLINED,
        "expire": AuditActionType.INVITATION_EXPIRED,
        "cancel": AuditActionType.INVITATION_CANCELED,
        "resend": AuditActionType.INVITATION_RESENT,
    }

    # Security event mappings
    SECURITY_ACTIONS = {
        "access_denied": AuditActionType.ACCESS_DENIED,
        "unauthorized_attempt": AuditActionType.UNAUTHORIZED_ACCESS_ATTEMPT,
    }

    @classmethod
    def get_crud_action(cls, entity_type, operation):
        """
        Get the appropriate audit action for a CRUD operation.
        """
        return cls.CRUD_ACTIONS[entity_type][operation]

    @classmethod
    def get_status_action(cls, entity_type, new_status):
        """
        Get the appropriate audit action for a status change.
        """
        return cls.STATUS_ACTIONS[entity_type][new_status]

    @classmethod
    def get_member_action(cls, entity_type, operation):
        """
        Get the appropriate audit action for member management.
        """
        return cls.MEMBER_ACTIONS[entity_type][operation]

    @classmethod
    def get_auth_action(cls, operation):
        """
        Get the appropriate audit action for authentication events.
        """
        return cls.AUTH_ACTIONS[operation]

    @classmethod
    def get_file_action(cls, operation):
        """
        Get the appropriate audit action for file operations.
        """
        return cls.FILE_ACTIONS[operation]

    @classmethod
    def get_invitation_action(cls, operation):
        """
        Get the appropriate audit action for invitation operations.
        """
        return cls.INVITATION_ACTIONS[operation]

    @classmethod
    def get_security_action(cls, operation):
        """
        Get the appropriate audit action for security events.
        """
        return cls.SECURITY_ACTIONS[operation]


def get_action_category(action_type):
    """
    Get the category of an audit action type.
    """
    action_value = action_type.value if hasattr(action_type, "value") else action_type

    # Authentication & Authorization
    auth_actions = [
        "login_success",
        "login_failed",
        "logout",
        "password_changed",
        "password_reset_requested",
        "password_reset_completed",
    ]

    # User Management
    user_actions = [
        "user_created",
        "user_updated",
        "user_deleted",
        "user_profile_updated",
    ]

    # Organization Management
    org_actions = [
        "organization_created",
        "organization_updated",
        "organization_deleted",
        "organization_status_changed",
        "organization_archived",
        "organization_activated",
        "organization_closed",
        "organization_member_added",
        "organization_member_removed",
        "organization_member_role_changed",
        "organization_member_updated",
    ]

    # Workspace Management
    workspace_actions = [
        "workspace_created",
        "workspace_updated",
        "workspace_deleted",
        "workspace_status_changed",
        "workspace_archived",
        "workspace_activated",
        "workspace_closed",
        "workspace_admin_changed",
        "workspace_reviewer_assigned",
    ]

    # Team Management
    team_actions = [
        "team_created",
        "team_updated",
        "team_deleted",
        "team_member_added",
        "team_member_removed",
        "team_member_role_changed",
        "workspace_team_created",
        "workspace_team_updated",
        "workspace_team_deleted",
    ]

    # Entry Management
    entry_actions = [
        "entry_created",
        "entry_updated",
        "entry_deleted",
        "entry_status_changed",
        "entry_submitted",
        "entry_reviewed",
        "entry_approved",
        "entry_rejected",
        "entry_flagged",
        "entry_unflagged",
    ]

    # File Management
    file_actions = [
        "file_uploaded",
        "file_downloaded",
        "file_deleted",
        "attachment_added",
        "attachment_removed",
        "attachment_updated",
    ]

    # Remittance Management
    remittance_actions = [
        "remittance_created",
        "remittance_updated",
        "remittance_deleted",
        "remittance_status_changed",
        "remittance_paid",
        "remittance_partially_paid",
        "remittance_overdue",
        "remittance_canceled",
    ]

    # Security Events
    security_actions = ["access_denied", "unauthorized_access_attempt"]

    if action_value in auth_actions:
        return "Authentication & Authorization"
    elif action_value in user_actions:
        return "User Management"
    elif action_value in org_actions:
        return "Organization Management"
    elif action_value in workspace_actions:
        return "Workspace Management"
    elif action_value in team_actions:
        return "Team Management"
    elif action_value in entry_actions:
        return "Entry Management"
    elif action_value in file_actions:
        return "File Management"
    elif action_value in remittance_actions:
        return "Remittance Management"
    elif action_value in security_actions:
        return "Security Events"
    else:
        return "Other"


def is_security_related(action_type):
    """
    Check if an audit action type is security-related.
    """
    action_value = action_type.value if hasattr(action_type, "value") else action_type

    security_actions = [
        "login_failed",
        "access_denied",
        "unauthorized_access_attempt",
        "permission_revoked",
    ]

    return action_value in security_actions


# =============================================================================
# AUDIT LOGGING UTILITIES
# =============================================================================


def safe_audit_log(func):
    """Decorator to safely handle audit logging without breaking main operations."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError:
            # Re-raise validation errors as they indicate incorrect usage
            raise
        except Exception as e:
            logger.error(f"Audit logging failed in {func.__name__}: {e}", exc_info=True)
            # Don't re-raise to avoid breaking main operations
            return None

    return wrapper


def truncate_metadata(metadata, max_size=None):
    """Truncate metadata to prevent database issues with large data"""
    if max_size is None:
        max_size = AuditConfig.MAX_METADATA_SIZE

    metadata_str = json.dumps(metadata, default=str)

    if len(metadata_str) <= max_size:
        return metadata

    # If too large, remove less critical fields
    truncated = metadata.copy()

    # Remove large fields first
    large_fields = ["user_agent", "request_headers", "response_data"]
    for field in large_fields:
        if field in truncated and len(json.dumps(truncated, default=str)) > max_size:
            truncated[field] = f"[TRUNCATED - was {len(str(truncated[field]))} chars]"

    # If still too large, truncate string values
    if len(json.dumps(truncated, default=str)) > max_size:
        for key, value in truncated.items():
            if isinstance(value, str) and len(value) > 100:
                truncated[key] = value[:100] + "..."

    return truncated


def should_log_model(model_class):
    """Determine if a model should be automatically logged"""
    if not AuditConfig.ENABLE_AUTOMATIC_LOGGING:
        return False

    # Exclude Django internal models
    excluded_models = {
        "Session",
        "LogEntry",
        "AuditTrail",
        "ContentType",
        "Permission",
        "Group",
        "Migration",
        "Token",
    }

    # Exclude models by app
    excluded_apps = {"admin", "contenttypes", "sessions", "auth"}
    app_label = getattr(model_class._meta, "app_label", "")

    if app_label in excluded_apps:
        return False

    if model_class.__name__ in excluded_models:
        return False

    # Only log specific business models
    business_models = {
        "Organization",
        "Workspace",
        "Entry",
        "Team",
        "User",
        "Invitation",
        "Remittance",
    }

    return model_class.__name__ in business_models


class AuditSignalMixin:
    """
    Mixin to add audit context to model instances.
    Use this in your views to provide context for signal-based logging.
    """

    def set_audit_context(self, user, action_context=None):
        """Set audit context on the model instance"""
        self._audit_user = user
        self._audit_context = action_context or {}
