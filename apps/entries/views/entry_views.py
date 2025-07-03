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
