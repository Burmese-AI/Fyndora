from django.contrib.contenttypes.models import ContentType
from apps.core.utils import model_update

from .models import AuditTrail


def audit_create(*, user, action_type, target_entity, metadata=None):
    """
    Service to create an audit log entry.
    """
    target_entity_type = ContentType.objects.get_for_model(target_entity)
    target_entity_id = target_entity.pk

    audit = AuditTrail()
    data = {
        "user": user,
        "action_type": action_type,
        "target_entity_id": target_entity_id,
        "target_entity_type": target_entity_type,
        "metadata": metadata,
    }

    return model_update(audit, data)
