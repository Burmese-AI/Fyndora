from django.db.models import Q
from .models import Entry
from apps.organizations.models import Organization, OrganizationMember
from apps.teams.models import TeamMember
from django.contrib.contenttypes.models import ContentType
from .constants import EntryType, EntryStatus
from django.db.models import Sum
from django.utils.timezone import now
from datetime import timedelta


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
    )

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
