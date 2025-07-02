from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Sum, Count
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.utils.timezone import now

from apps.organizations.models import Organization, OrganizationMember
from apps.teams.models import TeamMember
from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.organizations.selectors import get_org_members
from apps.teams.selectors import get_team_members

from .constants import EntryStatus, EntryType
from .models import Entry


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
  

def get_org_entries(
    organization: Organization,
    *,
    entry_types: list[EntryType] = list(EntryType),
    statuses: list[EntryStatus] = list(EntryStatus),
    submitter_types: list[str] = ["org_member", "team_member"],
    sort_by: str = None,
    prefetch_attachments: bool = False,
    annotate_attachment_count: bool = False,
):
    """
    Get organization entries with flexible filtering options.

    Args:
        organization: Organization to query
        entry_types: Which entry types to include (default: all)
        statuses: Which statuses to include (default: all)
        submitter_types: ['org_member', 'team_member'] or one of them
        sort_by: Field to sort by (e.g., 'created_at' or '-amount')
        prefetch_attachments: Load attachments in same query
        annotate_attachment_count: Add attachment_count annotation

    Returns:
        Filtered and optimized Entry queryset
    """

    # Prepare content types and IDs for filtering
    filters = Q()

    if "org_member" in submitter_types:
        org_member_type = ContentType.objects.get_for_model(OrganizationMember)
        org_member_ids = OrganizationMember.objects.filter(
            organization=organization
        ).values_list("pk", flat=True)
        filters |= Q(
            submitter_content_type=org_member_type,
            submitter_object_id__in=org_member_ids,
        )

    if "team_member" in submitter_types:
        team_member_type = ContentType.objects.get_for_model(TeamMember)
        team_member_ids = TeamMember.objects.filter(
            organization_member__organization=organization
        ).values_list("pk", flat=True)
        filters |= Q(
            submitter_content_type=team_member_type,
            submitter_object_id__in=team_member_ids,
        )

    # Build the base queryset
    queryset = Entry.objects.filter(
        filters,
        entry_type__in=entry_types,
        status__in=statuses,
    )

    # Prepare prefetch queries
    generic_prefetch_queries = []
    generic_prefetch = None

    # Prefetch organization members with users
    if "org_member" in submitter_types:
        org_member_queryset = OrganizationMember.objects.select_related("user")
        generic_prefetch_queries.append(org_member_queryset)

    # Prefetch team members with related data
    if "team_member" in submitter_types:
        team_member_queryset = TeamMember.objects.select_related(
            "organization_member", "team"
        )
        generic_prefetch_queries.append(team_member_queryset)

    # Apply prefetches
    if generic_prefetch_queries:
        generic_prefetch = GenericPrefetch("submitter", generic_prefetch_queries)

    if generic_prefetch:
        queryset = queryset.prefetch_related(generic_prefetch)

    # Optionally prefetch attachments
    if prefetch_attachments:
        queryset = queryset.prefetch_related("attachments")

    # Optionally annotate with attachment count
    if annotate_attachment_count:
        queryset = queryset.annotate(attachment_count=Count("attachments"))

    # Apply sorting if specified
    if sort_by:
        queryset = queryset.order_by(sort_by)

    return queryset


def get_entries(
    *,
    organization: Organization = None,
    workspace: Workspace = None,
    workspace_team: WorkspaceTeam = None,
    entry_type: EntryType,
    status: EntryStatus = None,
):
    """
    Get entries with flexible filtering options.

    Args:
        organization: Organization to query
        workspace: Workspace to query
        workspace_team: Workspace team to query
        entry_type: Entry type to query
        status: Status to query
    """    
    
    generic_prefetch_queries = []
    submitter_type = None
    member_ids = []
    
    
    #if organization expense, then organization is required
    #When getting organization expense, org member needs to be prefetched
    #if workspace expense, then workspace is required
    #When getting workspace expense, org member needs to be prefetched
    if entry_type == EntryType.ORG_EXP or entry_type == EntryType.WORKSPACE_EXP:
        submitter_type = ContentType.objects.get_for_model(OrganizationMember)
        org_member_queryset = get_org_members(prefetch_user=True)
        generic_prefetch_queries.append(org_member_queryset)
        if entry_type == EntryType.ORG_EXP:
            #Get all org members of the organization
            member_ids = get_org_members(organization=organization).values_list("pk", flat=True)
        else:
            #Get all org members of the workspace's organization
            member_ids = get_org_members(workspace=workspace).values_list("pk", flat=True)
            
    #if the rest, then workspace_team is required
    #When getting the rest, team member needs to be prefetched
    else:
        submitter_type = ContentType.objects.get_for_model(TeamMember)
        workspace_member_queryset = get_team_members(prefetch_user=True)
        generic_prefetch_queries.append(workspace_member_queryset)
        member_ids = get_team_members(workspace_team).values_list("pk", flat=True)


    generic_prefetch = GenericPrefetch("submitter", generic_prefetch_queries)

    # Base queryset
    queryset = Entry.objects.filter(
        submitter_content_type=submitter_type,
        submitter_object_id__in=member_ids,
        entry_type=entry_type
    ).annotate(
        attachment_count=Count("attachments")
    ).prefetch_related(
        generic_prefetch
    )

    if status:
        queryset = queryset.filter(status=status)

    return queryset

def get_total_org_expenses(organization: Organization):
    queryset = get_entries(organization=organization, entry_type=EntryType.ORG_EXP, status=EntryStatus.APPROVED)
    return queryset.aggregate(total=Sum("amount"))["total"] or 0


def get_this_month_org_expenses(organization: Organization):
    today = now().date()
    start_of_month = today.replace(day=1)
    queryset = get_entries(organization=organization, entry_type=EntryType.ORG_EXP, status=EntryStatus.APPROVED).filter(
        created_at__gte=start_of_month, status=EntryStatus.APPROVED
    )
    return queryset.aggregate(total=Sum("amount"))["total"] or 0


def get_average_monthly_org_expenses(organization: Organization):
    today = now().date()
    one_year_ago = today - timedelta(days=365)

    queryset = get_entries(organization=organization, entry_type=EntryType.ORG_EXP, status=EntryStatus.APPROVED).filter(
        created_at__gte=one_year_ago, status=EntryStatus.APPROVED
    )
    total = queryset.aggregate(total=Sum("amount"))["total"] or 0

    return total / 12


def get_last_month_org_expenses(organization: Organization):
    today = now().date()
    start_of_this_month = today.replace(day=1)
    end_of_last_month = start_of_this_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)

    queryset = get_entries(organization=organization, entry_type=EntryType.ORG_EXP, status=EntryStatus.APPROVED).filter(
        created_at__date__gte=start_of_last_month,
        created_at__date__lte=end_of_last_month,
        status=EntryStatus.APPROVED,
    )
    return queryset.aggregate(total=Sum("amount"))["total"] or 0
