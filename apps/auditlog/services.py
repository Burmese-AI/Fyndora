import logging
import uuid
from decimal import Decimal
from datetime import datetime, date, timezone
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
    Handles Django model instances by converting them to strings.
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
        # For Django model instances and other objects, convert to string
        return str(obj)


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
            # Priority 1: Target entity is a workspace
            if isinstance(target_entity, Workspace):
                workspace = target_entity

            # Priority 2: Target entity has direct workspace relationship
            elif hasattr(target_entity, "workspace") and target_entity.workspace:
                workspace = target_entity.workspace

            # Priority 3: Target entity has workspace through team relationship
            elif (
                hasattr(target_entity, "workspace_team")
                and target_entity.workspace_team
            ):
                workspace = target_entity.workspace_team.workspace

            # Priority 4: Target entity has workspace through team (direct team relationship)
            elif hasattr(target_entity, "team") and target_entity.team:
                # Check if team has workspace relationships
                if hasattr(target_entity.team, "workspace_teams"):
                    workspace_team = target_entity.team.workspace_teams.first()
                    if workspace_team:
                        workspace = workspace_team.workspace

            # Priority 5: Target entity is an organization member, get their primary workspace
            elif hasattr(target_entity, "administered_workspaces"):
                # If target is an organization member who administers workspaces
                administered_workspace = target_entity.administered_workspaces.first()
                if administered_workspace:
                    workspace = administered_workspace

            # Priority 6: Target entity is related to organization, get organization's first workspace
            elif hasattr(target_entity, "organization") and target_entity.organization:
                if hasattr(target_entity.organization, "workspaces"):
                    org_workspace = target_entity.organization.workspaces.filter(
                        status="active"
                    ).first()
                    if org_workspace:
                        workspace = org_workspace

        # Fallback: If still no workspace and user has organization memberships
        if workspace is None and user and hasattr(user, "organization_memberships"):
            active_membership = user.organization_memberships.filter(
                is_active=True, organization__status="active"
            ).first()
            if active_membership and hasattr(
                active_membership.organization, "workspaces"
            ):
                user_workspace = active_membership.organization.workspaces.filter(
                    status="active"
                ).first()
                if user_workspace:
                    workspace = user_workspace

        # Auto-detect organization from workspace, target entity, or user
        organization = None

        # Priority 1: From workspace
        if workspace and hasattr(workspace, "organization"):
            organization = workspace.organization

        # Priority 2: From target entity (direct organization relationship)
        elif target_entity and hasattr(target_entity, "organization"):
            organization = target_entity.organization

        # Priority 3: From target entity's workspace (if target has workspace)
        elif (
            target_entity
            and hasattr(target_entity, "workspace")
            and target_entity.workspace
        ):
            if hasattr(target_entity.workspace, "organization"):
                organization = target_entity.workspace.organization

        # Priority 4: From target entity's team organization (if target is team-related)
        elif target_entity and hasattr(target_entity, "team") and target_entity.team:
            if hasattr(target_entity.team, "organization"):
                organization = target_entity.team.organization

        # Priority 5: From user's active organization memberships
        elif user and hasattr(user, "organization_memberships"):
            # Try to get user's primary/active organization
            active_membership = user.organization_memberships.filter(
                is_active=True, organization__status="active"
            ).first()
            if active_membership:
                organization = active_membership.organization

        # Priority 6: From user's any organization membership (fallback)
        elif user and hasattr(user, "organization_memberships"):
            any_membership = user.organization_memberships.filter(
                organization__status="active"
            ).first()
            if any_membership:
                organization = any_membership.organization

        # Ensure metadata is JSON serializable
        serializable_metadata = (
            make_json_serializable(metadata) if metadata is not None else None
        )

        data = {
            "user": user,
            "action_type": action_type,
            "target_entity_id": target_entity_id,
            "target_entity_type": target_entity_type,
            "organization": organization,
            "workspace": workspace,
            "metadata": serializable_metadata,
        }

        return model_update(audit, data)

    except Exception as e:
        logger.error(f"Failed to create audit log: {e}", exc_info=True)
        return None


def audit_create_authentication_event(
    *, user, action_type, workspace=None, metadata=None
):
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
        workspace=workspace,
        metadata=enhanced_metadata,
    )


def audit_create_security_event(
    *, user, action_type, target_entity=None, workspace=None, metadata=None
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    return audit_create(
        user=user,
        action_type=action_type,
        target_entity=target_entity,
        workspace=workspace,
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
    expired_logs = get_expired_logs_queryset(
        action_type=action_type, override_days=override_days
    )

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
