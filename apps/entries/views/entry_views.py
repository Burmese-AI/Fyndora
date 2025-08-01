from typing import Any
from django.db.models.query import QuerySet
from django.http.response import HttpResponse as HttpResponse
from django.urls import reverse

from apps.core.views.base_views import BaseGetModalFormView
from ..constants import CONTEXT_OBJECT_NAME, EntryStatus, EntryType
from ..selectors import get_entries
from ..services import delete_entry
from apps.core.views.mixins import WorkspaceTeamRequiredMixin
from .mixins import (
    EntryFormMixin,
    EntryRequiredMixin,
)
from .base_views import (
    TeamLevelEntryView,
)
from ..forms import (
    UpdateWorkspaceTeamEntryForm,
    CreateWorkspaceTeamEntryForm,
)
from apps.core.views.crud_base_views import (
    BaseCreateView,
    BaseDeleteView,
    BaseListView,
    BaseUpdateView,
)
from ..models import Entry
from apps.core.views.service_layer_mixins import (
    HtmxTableServiceMixin,
    HtmxRowResponseMixin,
)
from ..services import create_entry_with_attachments


class WorkspaceTeamEntryListView(
    WorkspaceTeamRequiredMixin,
    TeamLevelEntryView,
    BaseListView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"
    template_name = "entries/team_level_entry.html"

    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
            annotate_attachment_count=True,
        )


class WorkspaceTeamEntryCreateView(
    WorkspaceTeamRequiredMixin,
    TeamLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    HtmxTableServiceMixin,
    BaseCreateView,
):
    model = Entry
    form_class = CreateWorkspaceTeamEntryForm
    modal_template_name = "entries/components/create_modal.html"
    table_template_name = "entries/partials/table.html"
    context_object_name = CONTEXT_OBJECT_NAME

    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
            annotate_attachment_count=True,
        )

    def get_modal_title(self) -> str:
        return "Organization Expense"

    def get_post_url(self) -> str:
        return reverse(
            "workspace_team_entry_create",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "workspace_team_id": self.workspace_team.pk,
            },
        )

    def perform_service(self, form):
        create_entry_with_attachments(
            amount=form.cleaned_data["amount"],
            occurred_at=form.cleaned_data["occurred_at"],
            description=form.cleaned_data["description"],
            attachments=form.cleaned_data["attachment_files"],
            entry_type=form.cleaned_data["entry_type"],
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            currency=form.cleaned_data["currency"],
            submitted_by_org_member=self.org_member if self.is_org_admin else None,
            submitted_by_team_member=self.workspace_team_member
        )


class WorkspaceTeamEntryUpdateView(
    WorkspaceTeamRequiredMixin,
    EntryRequiredMixin,
    TeamLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    HtmxRowResponseMixin,
    BaseUpdateView,
):
    model = Entry
    form_class = UpdateWorkspaceTeamEntryForm
    modal_template_name = "entries/components/update_modal.html"
    row_template_name = "entries/partials/row.html"

    def get_queryset(self):
        return Entry.objects.filter(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            pk=self.entry.pk,
        )

    def get_modal_title(self) -> str:
        return ""

    def get_post_url(self) -> str:
        return reverse(
            "workspace_team_entry_update",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "workspace_team_id": self.workspace_team.pk,
                "pk": self.instance.pk,
            },
        )

    def perform_service(self, form):
        from ..services import update_entry_status, update_entry_user_inputs

        if self.entry.status == EntryStatus.PENDING:
            update_entry_user_inputs(
                entry=self.entry,
                organization=self.organization,
                amount=form.cleaned_data["amount"],
                occurred_at=form.cleaned_data["occurred_at"],
                description=form.cleaned_data["description"],
                currency=form.cleaned_data["currency"],
                attachments=form.cleaned_data["attachment_files"],
                replace_attachments=True,
            )

        # If the status has changed, update the status
        if self.entry.status != form.cleaned_data["status"]:
            update_entry_status(
                entry=self.entry,
                status=form.cleaned_data["status"],
                last_status_modified_by=self.org_member,
                status_note=form.cleaned_data["status_note"],
            )


class WorkspaceTeamEntryDeleteView(
    WorkspaceTeamRequiredMixin,
    EntryRequiredMixin,
    TeamLevelEntryView,
    HtmxTableServiceMixin,
    BaseDeleteView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"

    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            workspace_team=self.workspace_team,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
            annotate_attachment_count=True,
        )

    def perform_service(self, form):
        delete_entry(self.entry)
