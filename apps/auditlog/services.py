import logging

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from apps.core.utils import model_update
from apps.workspaces.models import Workspace

from .models import AuditTrail

User = get_user_model()
logger = logging.getLogger(__name__)


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

        data = {
            "workspace": workspace,
            "user": user,
            "action_type": action_type,
            "target_entity_id": target_entity_id,
            "target_entity_type": target_entity_type,
            "metadata": metadata or {},
        }

        return model_update(audit, data)

    except Exception as e:
        logger.error(f"Failed to create audit log: {e}", exc_info=True)
        return None


def audit_create_authentication_event(*, user, action_type, metadata=None):
    """
    Service to create authentication-related audit log entries.
    """
    enhanced_metadata = metadata or {}
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
    enhanced_metadata = metadata or {}
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
