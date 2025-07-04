from typing import List

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Count, QuerySet
from django.contrib.contenttypes.prefetch import GenericPrefetch

from apps.organizations.models import Organization, OrganizationMember
from apps.teams.models import TeamMember
from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.organizations.selectors import get_org_members
from apps.teams.selectors import get_team_members

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
    Get entries with flexible filtering options, supporting multiple entry types.

    Args:
        organization: Organization to query
        workspace: Workspace to query
        workspace_team: Workspace team to query
        entry_types: List of entry types to query
        status: Status to filter by
        prefetch_attachments: Whether to prefetch related attachments
        sort_by: Optional field name to sort results
        annotate_attachment_count: Whether to annotate attachment count
    """
    if not entry_types:
        raise ValueError("At least one entry type must be provided.")

    # --- 1. Split Entry Types ---
    org_entry_types = [
        et for et in entry_types if et in (EntryType.ORG_EXP, EntryType.WORKSPACE_EXP)
    ]
    team_entry_types = [et for et in entry_types if et not in org_entry_types]

    filters = Q()
    prefetches = []

    # --- 2. Org Entries (OrganizationMember submitter) ---
    if org_entry_types:
        if not organization and not workspace:
            raise ValueError(
                "Either organization or workspace is required for organization level entry types."
            )

        submitter_ct = ContentType.objects.get_for_model(OrganizationMember)
        org_members = get_org_members(
            organization=organization if organization else None,
            workspace=workspace if workspace else None,
            prefetch_user=True,
        )
        org_member_ids = org_members.values_list("pk", flat=True)

        filters |= Q(
            submitter_content_type=submitter_ct,
            submitter_object_id__in=org_member_ids,
            entry_type__in=org_entry_types,
        )
        prefetches.append(GenericPrefetch("submitter", [org_members]))

    # --- 3. Team Entries (TeamMember submitter) ---
    if team_entry_types:
        if not workspace_team:
            raise ValueError("workspace_team is required for team level entry types.")

        submitter_ct = ContentType.objects.get_for_model(TeamMember)
        team_members = get_team_members(team=workspace_team.team, prefetch_user=True)
        team_member_ids = team_members.values_list("pk", flat=True)

        filters |= Q(
            submitter_content_type=submitter_ct,
            submitter_object_id__in=team_member_ids,
            entry_type__in=team_entry_types,
        )
        prefetches.append(GenericPrefetch("submitter", [team_members]))

    # --- 4. Final Query ---
    if not filters:
        return Entry.objects.none()

    queryset = Entry.objects.filter(filters)

    for prefetch in prefetches:
        queryset = queryset.prefetch_related(prefetch)

    if annotate_attachment_count:
        queryset = queryset.annotate(attachment_count=Count("attachments"))

    if status:
        queryset = queryset.filter(status=status)

    if sort_by:
        queryset = queryset.order_by(sort_by)

    if prefetch_attachments:
        queryset = queryset.prefetch_related("attachments")
    return queryset


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
