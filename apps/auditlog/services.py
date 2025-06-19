from django.contrib.contenttypes.models import ContentType

from apps.core.utils import model_update
from apps.workspaces.models import Workspace

from .models import AuditTrail


def audit_create(*, user, action_type, target_entity, workspace=None, metadata=None):
    """
    Service to create an audit log entry.
    """
    target_entity_type = ContentType.objects.get_for_model(target_entity)
    target_entity_id = target_entity.pk

    audit = AuditTrail()

    if workspace is None:
        if isinstance(target_entity, Workspace):
            workspace = target_entity
        elif hasattr(target_entity, "workspace") and target_entity.workspace:
            workspace = target_entity.workspace
        elif hasattr(target_entity, "workspace_team") and target_entity.workspace_team:
            workspace = target_entity.workspace_team.workspace

    data = {
        "workspace": workspace,
        "user": user,
        "action_type": action_type,
        "target_entity_id": target_entity_id,
        "target_entity_type": target_entity_type,
        "metadata": metadata,
    }

    return model_update(audit, data)
