from .models import AuditTrail
# from apps.entries.models import Entry


# TODO: Add workspace id when workspace is implemented
def get_audit_logs_for_workspace_with_filters(
    user_id=None,
    action_type=None,
    start_date=None,
    end_date=None,
    entity_id=None,
    entity_type=None,
    search_query=None,
):
    qs = AuditTrail.objects.select_related("user").all()
    if user_id:
        qs = qs.filter(user_id=user_id)
    if action_type:
        qs = qs.filter(action_type=action_type)
    if start_date:
        qs = qs.filter(timestamp__gte=start_date)
    if end_date:
        qs = qs.filter(timestamp__lte=end_date)
    if entity_id:
        qs = qs.filter(target_entity=entity_id)
    if entity_type:
        qs = qs.filter(target_entity_type=entity_type)

    if search_query:
        qs = qs.filter(metadata__icontains=search_query)

    return qs.order_by("-timestamp")
