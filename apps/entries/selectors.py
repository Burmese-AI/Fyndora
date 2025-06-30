from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Sum, Count
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.utils.timezone import now

from apps.organizations.models import Organization, OrganizationMember
from apps.teams.models import TeamMember
from apps.workspaces.models import Workspace

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


def get_org_expenses(organization: Organization):
    """
    Returns all organization expense entries submitted by members of the given organization,
    annotated with attachment count and optimized to avoid N+1 queries using prefetching.
    """

    # Get the ContentType for OrganizationMember model.
    org_member_type = ContentType.objects.get_for_model(OrganizationMember)

    # Get all OrganizationMember IDs that belong to the given organization
    # Because org exp entries can only be submitted by org members
    org_member_ids = OrganizationMember.objects.filter(
        organization=organization
    ).values_list("pk", flat=True)

    # Prepare the querysets for prefetching
    org_member_queryset = OrganizationMember.objects.select_related("user")

    # Use GenericPrefetch to tell Django how to prefetch 'submitter'
    generic_prefetch = GenericPrefetch("submitter", [org_member_queryset])

    # Fetch all org exp entries with those org members ids as submitter obj id
    entries = Entry.objects.filter(
        Q(
            submitter_content_type=org_member_type,
            submitter_object_id__in=org_member_ids,
        ),
        entry_type=EntryType.ORG_EXP,
    ).annotate(
        # Count how many attachments each entry has
        attachment_count=Count("attachments")
    )

    # Apply generic prefetch
    entries = entries.prefetch_related(generic_prefetch)

    return entries


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


def get_total_org_expenses(organization: Organization):
    queryset = get_org_expenses(organization).filter(status=EntryStatus.APPROVED)
    return queryset.aggregate(total=Sum("amount"))["total"] or 0


def get_this_month_org_expenses(organization: Organization):
    today = now().date()
    start_of_month = today.replace(day=1)
    queryset = get_org_expenses(organization).filter(created_at__gte=start_of_month, status=EntryStatus.APPROVED)
    return queryset.aggregate(total=Sum("amount"))["total"] or 0


def get_average_monthly_org_expenses(organization: Organization):
    today = now().date()
    one_year_ago = today - timedelta(days=365)

    qs = get_org_expenses(organization).filter(created_at__date__gte=one_year_ago, status=EntryStatus.APPROVED)
    total = qs.aggregate(total=Sum("amount"))["total"] or 0

    return total / 12


def get_last_month_org_expenses(organization: Organization):
    today = now().date()
    start_of_this_month = today.replace(day=1)
    end_of_last_month = start_of_this_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)

    queryset = get_org_expenses(organization).filter(
        created_at__date__gte=start_of_last_month,
        created_at__date__lte=end_of_last_month,
        status=EntryStatus.APPROVED,
    )
    return queryset.aggregate(total=Sum("amount"))["total"] or 0
