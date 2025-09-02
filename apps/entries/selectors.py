from typing import List
from decimal import Decimal

from django.db.models import Q, Count, QuerySet, F, Sum, DecimalField, ExpressionWrapper
from django.shortcuts import get_object_or_404

from apps.organizations.models import (
    Organization,
)
from apps.workspaces.models import Workspace, WorkspaceTeam

from .constants import EntryStatus, EntryType
from .models import Entry


# Selectors for Services and Views
def get_entries(
    *,
    organization: Organization = None,
    workspace: Workspace = None,
    workspace_team: WorkspaceTeam = None,
    entry_types: List[str],
    statuses: List[str] = [],
    type_filter: str = None,
    workspace_team_id: str = None,
    workspace_id: str = None,
    search: str = None,
    prefetch_attachments: bool = False,
    annotate_attachment_count: bool = False,
) -> QuerySet:
    """
    Get entries for a specific organization, workspace, or workspace team.
    """

    if not entry_types:
        raise ValueError("At least one entry type must be provided.")

    expense_entry_types = [
        et for et in entry_types if et in (EntryType.ORG_EXP, EntryType.WORKSPACE_EXP)
    ]
    team_entry_types = [et for et in entry_types if et not in expense_entry_types]

    filters = Q()

    if expense_entry_types:
        expense_filter = Q(entry_type__in=expense_entry_types)
        if workspace:
            expense_filter &= Q(workspace=workspace)
        elif organization:
            expense_filter &= Q(organization=organization)
        filters |= expense_filter

    if team_entry_types:
        if workspace_team:
            team_filter = Q(
                entry_type__in=team_entry_types,
                workspace_team=workspace_team,
            )
        elif workspace:
            team_filter = Q(
                entry_type__in=team_entry_types,
                workspace=workspace,
            )
        elif organization:
            team_filter = Q(
                entry_type__in=team_entry_types,
                organization=organization,
            )
        else:
            # If no context is provided, still create a filter for team entry types for testing edge purposes..
            team_filter = Q(entry_type__in=team_entry_types)

        filters |= team_filter

    if not filters:
        return Entry.objects.none()

    queryset = Entry.objects.filter(filters)
    if annotate_attachment_count:
        queryset = queryset.annotate(
            attachment_count=Count(
                "attachments", filter=Q(attachments__deleted_at__isnull=True)
            )
        )

    # Apply additional filters
    if statuses:
        queryset = queryset.filter(status__in=statuses)
    if type_filter:
        queryset = queryset.filter(entry_type=type_filter)
    if workspace_team_id:
        queryset = queryset.filter(workspace_team__pk=workspace_team_id)
    if workspace_id:
        queryset = queryset.filter(workspace__pk=workspace_id)
    if search:
        queryset = queryset.filter(Q(description__icontains=search))

    if prefetch_attachments:
        queryset = queryset.prefetch_related("attachments")

    queryset = queryset.select_related(
        "organization",
        "workspace",
        "workspace_team",
        "currency",
        "org_exchange_rate_ref",
        "workspace_exchange_rate_ref",
        "submitted_by_org_member__user",
        "submitted_by_team_member__organization_member__user",
        "last_status_modified_by__user",
    )

    return queryset.order_by("-occurred_at")


def get_total_amount_of_entries(
    *,
    entry_type: EntryType,
    entry_status: EntryStatus,
    workspace_team: WorkspaceTeam = None,
    workspace: Workspace = None,
    org: Organization = None,
) -> Decimal:
    """
    Get the total converted amount of entries (amount * exchange_rate_used)
    for a specific entry type and status within the given workspace team.

    Args:
        entry_type (EntryType): The type of entry to filter by.
        entry_status (EntryStatus): The status of the entries to include.
        workspace_team (WorkspaceTeam): The team whose entries to aggregate.

    Returns:
        Decimal: The total converted amount of matching entries.
    """
    object_to_get_entries_from = workspace_team or workspace or org
    total = object_to_get_entries_from.entries.filter(
        entry_type=entry_type, status=entry_status
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("amount") * F("exchange_rate_used"),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        )
    )["total"]

    return total or Decimal("0.00")


def get_entry(pk, required_attachment_count=False):
    queryset = Entry.objects.all()
    if required_attachment_count:
        queryset = queryset.annotate(
            attachment_count=Count(
                "attachments", filter=Q(attachments__deleted_at__isnull=True)
            )
        )
    return get_object_or_404(queryset, pk=pk)
