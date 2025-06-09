from django.db.models import Q

from .models import AuditTrail
from apps.entries.models import Entry


def get_audit_logs_for_workspace_with_filters(
    workspace_id,
    user_id=None,
    action_type=None,
    start_date=None,
    end_date=None,
    entity_id=None,
    entity_type=None,
):
    # Get all related entity IDs for this workspace
    entry_ids = Entry.objects.filter(workspace_id=workspace_id).values_list(
        "id", flat=True
    )
    # TODO: Uncomment this when models are created
    # remittance_ids = Remittance.objects.filter(workspace_id=workspace_id).values_list('id', flat=True)

    q_workspace = Q(target_entity=workspace_id, target_entity_type="workspace")
    q_entry = Q(target_entity__in=entry_ids, target_entity_type="entry")
    # q_remittance = Q(target_entity__in=remittance_ids, target_entity_type="remittance")

    combined_q = q_workspace | q_entry  # | q_remittance

    qs = AuditTrail.objects.filter(combined_q)
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if action_type is not None:
        qs = qs.filter(action_type=action_type)
    if start_date is not None:
        qs = qs.filter(timestamp__gte=start_date)
    if end_date is not None:
        qs = qs.filter(timestamp__lte=end_date)
    if entity_id is not None:
        qs = qs.filter(target_entity=entity_id)
    if entity_type is not None:
        qs = qs.filter(target_entity_type=entity_type)
    return qs
