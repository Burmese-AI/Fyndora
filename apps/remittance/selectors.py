from apps.remittance.models import Remittance


def get_remittances_with_filters(
    workspace_id,
    team_ids=None,
    statuses=None,
    start_date=None,
    end_date=None,
    search=None,
):
    """
    Fetches remittances for a given workspace and applies additional filters.
    """
    qs = Remittance.objects.select_related(
        "workspace_team__team",
        "workspace_team__workspace",
        "confirmed_by",
    ).filter(workspace_team__workspace_id=workspace_id)

    if team_ids:
        qs = qs.filter(workspace_team__team_id__in=team_ids)

    if statuses:
        qs = qs.filter(status__in=statuses)

    if start_date:
        qs = qs.filter(workspace_team__workspace__end_date__gte=start_date)

    if end_date:
        qs = qs.filter(workspace_team__workspace__end_date__lte=end_date)

    if search:
        qs = qs.filter(workspace_team__team__title__icontains=search)

    return qs
