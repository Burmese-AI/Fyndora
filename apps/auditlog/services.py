import logging
import uuid
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Optional

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.core.utils import model_update
from apps.workspaces.models import Workspace

from .models import AuditTrail
from .config import AuditConfig
from .constants import AuditActionType
from .selectors import get_expired_logs_queryset

User = get_user_model()
logger = logging.getLogger(__name__)


def make_json_serializable(obj):
    """
    Convert objects to JSON serializable format.
    Raises TypeError for truly non-serializable objects.
    """
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (uuid.UUID,)):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    else:
        # For truly non-serializable objects, raise an exception
        # instead of converting to string
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def audit_create(
    *, user, action_type, target_entity=None, workspace=None, metadata=None
):
    """
    Service to create an audit log entry.
    """
    try:
        if target_entity:
            target_entity_type = ContentType.objects.get_for_model(target_entity)
            target_entity_id = target_entity.pk
        else:
            # For actions without specific target (like failed logins)
            target_entity_type = None
            target_entity_id = None

        audit = AuditTrail()

        # Auto-detect workspace if not provided
        if workspace is None and target_entity:
            if isinstance(target_entity, Workspace):
                workspace = target_entity
            elif hasattr(target_entity, "workspace") and target_entity.workspace:
                workspace = target_entity.workspace
            elif (
                hasattr(target_entity, "workspace_team")
                and target_entity.workspace_team
            ):
                workspace = target_entity.workspace_team.workspace

        # Ensure metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata or {})

        data = {
            "workspace": workspace,
            "user": user,
            "action_type": action_type,
            "target_entity_id": target_entity_id,
            "target_entity_type": target_entity_type,
            "metadata": serializable_metadata,
        }

        return model_update(audit, data)

    except Exception as e:
        logger.error(f"Failed to create audit log: {e}", exc_info=True)
        return None


def audit_create_authentication_event(*, user, action_type, metadata=None):
    """
    Service to create authentication-related audit log entries.
    """
    enhanced_metadata = make_json_serializable(metadata or {})
    enhanced_metadata.update(
        {
            "event_category": "authentication",
            "is_security_related": True,
        }
    )

    return audit_create(
        user=user,
        action_type=action_type,
        target_entity=user,
        metadata=enhanced_metadata,
    )


def audit_create_security_event(
    *, user, action_type, target_entity=None, metadata=None
):
    """
    Service to create security-related audit log entries.
    """
    enhanced_metadata = make_json_serializable(metadata or {})
    enhanced_metadata.update(
        {
            "event_category": "security",
            "is_security_related": True,
            "requires_investigation": True,
        }
    )

    return audit_create(
        user=user,
        action_type=action_type,
        target_entity=target_entity,
        metadata=enhanced_metadata,
    )


def audit_cleanup_expired_logs(
    *,
    dry_run: bool = False,
    batch_size: Optional[int] = None,
    action_type: Optional[str] = None,
    override_days: Optional[int] = None,
) -> Dict[str, int]:
    """
    Clean up expired audit logs based on retention policies.
    """
    if batch_size is None:
        batch_size = AuditConfig.CLEANUP_BATCH_SIZE

    stats = {
        "authentication_deleted": 0,
        "default_deleted": 0,
        "total_deleted": 0,
        "dry_run": dry_run,
    }

    # Get expired logs queryset
    expired_logs = get_expired_logs_queryset(action_type=action_type, override_days=override_days)

    if action_type:
        # Clean up specific action type
        if dry_run:
            stats["total_deleted"] = expired_logs.count()
        else:
            stats["total_deleted"] = _delete_in_batches(expired_logs, batch_size)
    else:
        # Clean up by categories
        auth_actions = [
            AuditActionType.LOGIN_SUCCESS,
            AuditActionType.LOGIN_FAILED,
            AuditActionType.LOGOUT,
        ]

        # Authentication logs
        auth_expired = expired_logs.filter(action_type__in=auth_actions)
        if dry_run:
            stats["authentication_deleted"] = auth_expired.count()
        else:
            stats["authentication_deleted"] = _delete_in_batches(
                auth_expired, batch_size
            )

        # Default logs (non-auth)
        default_expired = expired_logs.exclude(action_type__in=auth_actions)
        if dry_run:
            stats["default_deleted"] = default_expired.count()
        else:
            stats["default_deleted"] = _delete_in_batches(default_expired, batch_size)

        stats["total_deleted"] = (
            stats["authentication_deleted"] + stats["default_deleted"]
        )

    logger.info(
        f"Audit log cleanup completed. "
        f"Deleted: {stats['total_deleted']} logs "
        f"(Auth: {stats['authentication_deleted']}, "
        f"Default: {stats['default_deleted']}) "
        f"Dry run: {dry_run}"
    )

    return stats


def _delete_in_batches(queryset, batch_size: int) -> int:
    """
    Delete records in batches to avoid memory issues.
    Internal helper function for safe batch deletion.
    """
    total_deleted = 0

    while True:
        with transaction.atomic():
            # Get a batch of IDs
            batch_ids = list(queryset.values_list("audit_id", flat=True)[:batch_size])

            if not batch_ids:
                break

            # Delete the batch
            deleted_count = AuditTrail.objects.filter(audit_id__in=batch_ids).delete()[
                0
            ]

            total_deleted += deleted_count

    return total_deleted
