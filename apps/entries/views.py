from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Subquery
from django.shortcuts import get_object_or_404
from typing import Any

from .models import Entry
from apps.organizations.models import Organization, OrganizationMember
from apps.teams.models import TeamMember
from apps.core.constants import PAGINATION_SIZE
from django.contrib.contenttypes.models import ContentType
from .constants import EntryType, EntryStatus


class OrganizationExpenseListView(LoginRequiredMixin, ListView):
    model = Entry
    template_name = "entries/index.html"
    context_object_name = "entries"
    paginate_by = PAGINATION_SIZE

    def dispatch(self, request, *args, **kwargs):
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Get content types
        org_member_type = ContentType.objects.get_for_model(OrganizationMember)
        team_member_type = ContentType.objects.get_for_model(TeamMember)

        # Subquery: IDs of Organization Members in this organization
        org_members_subquery = Subquery(
            OrganizationMember.objects.filter(organization=self.organization).values(
                "pk"
            )
        )

        # Subquery: IDs of TeamMembers whose OrganizationMember belongs to this org
        team_members_subquery = Subquery(
            TeamMember.objects.filter(
                organization_member__organization=self.organization
            ).values("pk")
        )

        # Main queryset filtering both submitter types
        return (
            Entry.objects.filter(
                Q(submitter_content_type=org_member_type)
                & Q(submitter_object_id__in=org_members_subquery)
                | Q(submitter_content_type=team_member_type)
                & Q(submitter_object_id__in=team_members_subquery)
            )
            .filter(entry_type=EntryType.WORKSPACE_EXP, status=EntryStatus.APPROVED)
            .select_related("submitter_content_type")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        return context
