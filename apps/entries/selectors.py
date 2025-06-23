from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Sum
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
    # Get content types
    org_member_type = ContentType.objects.get_for_model(OrganizationMember)
    team_member_type = ContentType.objects.get_for_model(TeamMember)

    # IDs of Organization Members in this organization
    org_member_ids = OrganizationMember.objects.filter(
        organization=organization
    ).values_list("pk", flat=True)

    # IDs of Team Members whose Organization Member belongs to this organization
    team_member_ids = TeamMember.objects.filter(
        organization_member__organization=organization
    ).values_list("pk", flat=True)

    query = Entry.objects.filter(
        Q(
            submitter_content_type=org_member_type,
            submitter_object_id__in=org_member_ids,
        )
        | Q(
            submitter_content_type=team_member_type,
            submitter_object_id__in=team_member_ids,
        ),
        entry_type=EntryType.ORG_EXP,
        status=EntryStatus.APPROVED,
    ).prefetch_related("attachments")

    return query


def get_total_org_expenses(organization: Organization):
    queryset = get_org_expenses(organization)
    return queryset.aggregate(total=Sum("amount"))["total"] or 0


def get_this_month_org_expenses(organization: Organization):
    today = now().date()
    start_of_month = today.replace(day=1)
    queryset = get_org_expenses(organization).filter(created_at__gte=start_of_month)
    return queryset.aggregate(total=Sum("amount"))["total"] or 0


def get_average_monthly_org_expenses(organization: Organization):
    today = now().date()
    one_year_ago = today - timedelta(days=365)

    qs = get_org_expenses(organization).filter(created_at__date__gte=one_year_ago)
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
    )
    return queryset.aggregate(total=Sum("amount"))["total"] or 0
