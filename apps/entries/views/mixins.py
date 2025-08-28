from typing import Any

from django.shortcuts import get_object_or_404

from ..models import Entry
from ..constants import EntryStatus, EntryType


class EntryRequiredMixin:
    entry = None
    instance = None
    attachments = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        entry_id = kwargs.get("pk")
        self.entry = get_object_or_404(Entry, pk=entry_id)
        self.instance = self.entry
        self.attachments = self.entry.attachments.all()

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["entry"] = self.entry
        context["attachments"] = self.attachments
        return context


class EntryFormMixin:
    form_class = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["org_member"] = self.org_member
        kwargs["organization"] = self.organization
        kwargs["is_org_admin"] = self.is_org_admin
        kwargs["is_workspace_admin"] = (
            self.is_workspace_admin if hasattr(self, "is_workspace_admin") else None
        )
        kwargs["is_operation_reviewer"] = (
            self.is_operation_reviewer
            if hasattr(self, "is_operation_reviewer")
            else None
        )
        kwargs["is_team_coordinator"] = (
            self.is_team_coordinator if hasattr(self, "is_team_coordinator") else None
        )
        kwargs["workspace"] = self.workspace if hasattr(self, "workspace") else None
        kwargs["workspace_team"] = (
            self.workspace_team if hasattr(self, "workspace_team") else None
        )
        kwargs["workspace_team_member"] = (
            self.workspace_team_member
            if hasattr(self, "workspace_team_member")
            else None
        )
        kwargs["workspace_team_role"] = (
            self.workspace_team_role if hasattr(self, "workspace_team_role") else None
        )
        return kwargs


class EntryUrlIdentifierMixin:
    def get_entry_type(self):
        raise NotImplementedError("You must implement get_entry_type() in the subclass")

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["entry_type"] = self.get_entry_type()
        return context


class StatusFilteringMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["status_options"] = [
            EntryStatus.PENDING,
            EntryStatus.REVIEWED,
            EntryStatus.APPROVED,
            EntryStatus.REJECTED,
        ]
        context["default_status_option"] = EntryStatus.PENDING
        context["filter_status_value"] = self.request.GET.get("status") or None
        context["filter_search_value"] = self.request.GET.get("search") or None
        return context


class TeamLevelEntryFiltering(StatusFilteringMixin):
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["type_options"] = [
            EntryType.INCOME,
            EntryType.DISBURSEMENT,
            EntryType.REMITTANCE,
        ]
        context["status_options"] = [
            EntryStatus.PENDING,
            EntryStatus.REVIEWED,
            EntryStatus.REJECTED,
        ]
        context["filter_type_value"] = self.request.GET.get("type")
        return context


class WorkspaceLevelEntryFiltering(TeamLevelEntryFiltering):
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # Gettting all workspace teams under the current workspace
        context["team_options"] = self.workspace.joined_teams.select_related(
            "team"
        ).all()
        # Overriding context values
        context["type_options"] = [
            EntryType.INCOME,
            EntryType.DISBURSEMENT,
            EntryType.REMITTANCE,
        ]
        context["status_options"] = [
            EntryStatus.PENDING,
            EntryStatus.REVIEWED,
            EntryStatus.REJECTED,
            EntryStatus.APPROVED,
        ]
        context["default_status_option"] = EntryStatus.REVIEWED
        context["filter_team_value"] = self.request.GET.get("team")
        return context
