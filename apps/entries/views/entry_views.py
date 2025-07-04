from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import (
    WorkspaceTeamRequiredMixin,
    WorkspaceTeamContextMixin,
)
from .base_views import BaseEntryListView
from ..constants import EntryType
from ..selectors import get_entries
from django.db.models import QuerySet
from typing import Any
from .mixins import (
    OrganizationMemberRequiredMixin,
    CreateEntryFormMixin,
    HtmxOobResponseMixin,
)
from .base_views import BaseEntryCreateView
from django.urls import reverse


class WorkspaceTeamEntryListView(
    LoginRequiredMixin,
    WorkspaceTeamRequiredMixin,
    WorkspaceTeamContextMixin,
    BaseEntryListView,
):
    template_name = "entries/team_level_entry.html"

    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            organization=self.organization,
            workspace_team=self.workspace_team,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
        )

class WorkspaceTeamEntryCreateView(
    LoginRequiredMixin,
    WorkspaceTeamRequiredMixin,
    WorkspaceTeamContextMixin,
    OrganizationMemberRequiredMixin,
    CreateEntryFormMixin,
    HtmxOobResponseMixin,
    BaseEntryCreateView,
):
    def get_modal_title(self) -> str:
        return ""
    
    def get_post_url(self) -> str:
        return reverse(
            "workspace_team_entry_create",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "workspace_team_id": self.workspace_team.pk,
            },
        )