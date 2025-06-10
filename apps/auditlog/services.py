from core.utils import model_update

from .models import AuditTrail


def audit_create(
    *, user, action_type, target_entity, target_entity_type, metadata=None
):
    """
    Service to create an audit log entry.
    """
    audit = AuditTrail()
    data = {
        "user": user,
        "action_type": action_type,
        "target_entity": target_entity,
        "target_entity_type": target_entity_type,
        "metadata": metadata,
    }

    return model_update(audit, data)
