from django.db.models import Q
from .models import Entry
from apps.organizations.models import Organization, OrganizationMember
from apps.teams.models import TeamMember
from django.contrib.contenttypes.models import ContentType
from .constants import EntryType, EntryStatus


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
        Q(submitter_content_type=org_member_type, submitter_object_id__in=org_member_ids) | Q(submitter_content_type=team_member_type, submitter_object_id__in=team_member_ids),
        entry_type=EntryType.ORG_EXP,
        status=EntryStatus.APPROVED
    )
    
    return query
