from .models import AuditTrail


def audit_create(*, user, action_type, target_entity, target_entity_type, metadata=None):
    """
    Service to create an audit log entry.
    """
    audit = AuditTrail(
        user=user,
        action_type=action_type,
        target_entity=target_entity,
        target_entity_type=target_entity_type,
        metadata=metadata,
    )
    audit.full_clean()
    audit.save()
    return audit
