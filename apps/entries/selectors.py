from typing import List
from decimal import Decimal

from django.db.models import Q, Count, QuerySet, F, Sum, DecimalField, ExpressionWrapper


from apps.organizations.models import (
    Organization,
    OrganizationMember,
)
from apps.teams.models import TeamMember
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
    sort_by: str = None,
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
    print(f">>> expense types => {expense_entry_types}")
    team_entry_types = [et for et in entry_types if et not in expense_entry_types]

    filters = Q()
    print(f">>>> team entry types => {team_entry_types}")
    if expense_entry_types:
        expense_filter = Q(entry_type__in=expense_entry_types)
        if organization:
            expense_filter &= Q(organization=organization)
        elif workspace:
            expense_filter &= Q(workspace=workspace)
        filters |= expense_filter
    print(f">>>> expense filter => {filters}")

    if team_entry_types:
        print(team_entry_types)
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

        filters |= team_filter
    print(f">>>> team filter => {filters}")

    if not filters:
        print(">>>> Returning None")
        return Entry.objects.none()

    queryset = Entry.objects.filter(filters).distinct()
    print(f">>>> queryset 0 => {queryset}")
    if annotate_attachment_count:
        queryset = queryset.annotate(attachment_count=Count("attachments"))

    # 🔹 Apply additional filters
    print(f"statuses => {statuses}")
    if statuses:
        queryset = queryset.filter(status__in=statuses)
    if type_filter:
        queryset = queryset.filter(entry_type=type_filter)
    if workspace_team_id:
        queryset = queryset.filter(workspace_team__pk=workspace_team_id)
    if workspace_id:
        queryset = queryset.filter(workspace_pk=workspace_id)
    if search:
        queryset = queryset.filter(Q(description__icontains=search))

    if sort_by:
        queryset = queryset.order_by(sort_by)

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

    return queryset


def get_total_amount_of_entries(
    *, entry_type: EntryType, entry_status: EntryStatus, workspace_team: WorkspaceTeam
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
    total = workspace_team.entries.filter(
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


# Selectors for Tests
def get_workspace_entries(*, workspace: Workspace):
    """
    Get all entries for a specific workspace.
    """
    return Entry.objects.filter(workspace=workspace)


def get_workspace_entries_by_status(*, workspace: Workspace, status):
    """
    Get entries for a specific workspace filtered by status.
    """
    return Entry.objects.filter(workspace=workspace, status=status)


def get_workspace_entries_by_type(*, workspace: Workspace, entry_type):
    """
    Get entries for a specific workspace filtered by entry type.
    """
    return Entry.objects.filter(workspace=workspace, entry_type=entry_type)


def get_workspace_entries_by_date_range(*, workspace: Workspace, start_date, end_date):
    """
    Get entries for a specific workspace created within a date range.
    """
    return Entry.objects.filter(
        workspace=workspace,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )


def get_user_workspace_entries(*, user, workspace: Workspace, status=None):
    """
    Get entries submitted by a specific user in a specific workspace.
    """
    # Get organization memberships for the user
    org_member_ids = OrganizationMember.objects.filter(user=user).values_list(
        "pk", flat=True
    )

    # Get team memberships for the user through organization memberships
    team_member_ids = TeamMember.objects.filter(
        organization_member__user=user
    ).values_list("pk", flat=True)

    # Base queryset filtering by the user's memberships as submitters and workspace
    queryset = Entry.objects.filter(
        Q(submitted_by_org_member__in=org_member_ids)
        | Q(submitted_by_team_member__in=team_member_ids),
        workspace=workspace,
    )

    if status:
        queryset = queryset.filter(status=status)

    return queryset


def get_workspace_team_entries(*, workspace_team, status=None, entry_type=None):
    """
    Get entries for a specific workspace team.
    """
    queryset = Entry.objects.filter(workspace_team=workspace_team)

    if status:
        queryset = queryset.filter(status=status)

    if entry_type:
        queryset = queryset.filter(entry_type=entry_type)

    return queryset
