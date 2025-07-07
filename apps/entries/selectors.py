from typing import List

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Count, QuerySet
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.shortcuts import get_object_or_404

from apps.organizations.models import Organization, OrganizationMember
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
    entry_types: List[EntryType],
    status: EntryStatus = None,
    prefetch_attachments: bool = False,
    sort_by: str = None,
    annotate_attachment_count: bool = False,
) -> QuerySet:
    
    
    """
    Get entries for a specific organization, workspace, or workspace team.

    Args:
        organization: Organization object
        workspace: Workspace object
        workspace_team: WorkspaceTeam object
        entry_types: List of EntryType objects
        status: EntryStatus object
        prefetch_attachments: Boolean to prefetch attachments

    Returns:
        QuerySet: QuerySet of Entry objects
        
    Notes:
        For expense entries, the organization or workspace is required.
        For team level entries, the workspace_team is required.
        At least one entry type must be provided.
    """
    
    if not entry_types:
        raise ValueError("At least one entry type must be provided.")

    # Split entry types
    expense_entry_types = [
        et for et in entry_types if et in (EntryType.ORG_EXP, EntryType.WORKSPACE_EXP)
    ]
    team_entry_types = [et for et in entry_types if et not in expense_entry_types]

    filters = Q()

    # Org/Workspace Expense Entries
    if expense_entry_types:
        # Filter entries based on expense entry types
        expense_entry_filters = Q(entry_type__in=expense_entry_types)
        # Filter entries based on organization members since org/workspace expense entries are associated with only organization members
        if organization:
            expense_entry_filters &= Q(organization_member_entries__organization=organization)
        elif workspace:
            expense_entry_filters &= Q(organization_member_entries__organization=workspace.organization)

        # Add expense entry filters to the main filters
        filters |= expense_entry_filters

    # Team Level Entries
    if team_entry_types:
        # Filter entries based on team entry types and workspace team using generic relation (team_member_entries)
        team_filter = Q(
            entry_type__in=team_entry_types,
            team_member_entries__team=workspace_team.team,
        )
        # Add team level filters to the main filters
        filters |= team_filter

    # Final Query
    if not filters:
        return Entry.objects.none()
    
    # Apply distinct to remove duplicate entries
    queryset = Entry.objects.filter(filters).distinct()

    if annotate_attachment_count:
        queryset = queryset.annotate(attachment_count=Count("attachments"))

    if status:
        queryset = queryset.filter(status=status)

    if sort_by:
        queryset = queryset.order_by(sort_by)

    if prefetch_attachments:
        queryset = queryset.prefetch_related("attachments")

    # Select related and prefetch related to optimize the query
    queryset = queryset.select_related(
        "submitter_content_type",
        "workspace",
        "workspace_team",
        "reviewed_by",
    ).prefetch_related(
        GenericPrefetch(
            "submitter",
            [OrganizationMember.objects.select_related("user"), TeamMember.objects.select_related("organization_member__user")],
        )
    )

    return queryset

def get_entry_by_scope(
    *,
    entry_id,
    organization: Organization = None,
    workspace: Workspace = None,
    workspace_team: WorkspaceTeam = None,
) -> Entry:
    """
    Fetch entry by ID, scoped to the given organization/workspace/team.
    Raises 404 if not found or not in scope.
    """

    queryset = Entry.objects.all()

    if organization:
        queryset = queryset.filter(workspace__organization=organization)

    if workspace:
        queryset = queryset.filter(workspace=workspace)

    if workspace_team:
        queryset = queryset.filter(workspace_team=workspace_team)

    return get_object_or_404(queryset, pk=entry_id)

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
    org_member_type = ContentType.objects.get_for_model(OrganizationMember)
    team_member_type = ContentType.objects.get_for_model(TeamMember)

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
        Q(
            submitter_content_type=org_member_type,
            submitter_object_id__in=org_member_ids,
        )
        | Q(
            submitter_content_type=team_member_type,
            submitter_object_id__in=team_member_ids,
        ),
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
