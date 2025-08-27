from django.db.models import Q
from apps.remittance.models import Remittance


def get_remittances_under_organization(
    organization_id, workspace_id=None, status=None, search_query=None
):
    """
    Return remittances under organization with Q object filtering.
    """
    try:
        # Build base Q object for organization filtering
        # that will used fetch workspace teams under organization
        base_q = Q(workspace_team__workspace__organization=organization_id)

        # Add workspace filter if provided
        if workspace_id:
            base_q &= Q(workspace_team__workspace=workspace_id)

        # Add status filter if provided
        if status:
            base_q &= Q(status=status)

        # Add search functionality if provided
        if search_query:
            search_q = Q(workspace_team__workspace__title__icontains=search_query) | Q(
                workspace_team__team__title__icontains=search_query
            )
            base_q &= search_q

        remittances = (
            Remittance.objects.filter(base_q)
            .select_related("workspace_team__workspace", "workspace_team__team")
            .order_by("-created_at")
        )

        # Add remaining amount calculation
        # to show overpaid amount in the table but not in -minus
        for remittance in remittances:
            remittance.remaining_amount = remittance.remaining_amount()

        return remittances
    except Exception:
        return None
