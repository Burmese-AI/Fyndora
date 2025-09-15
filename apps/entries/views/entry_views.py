from typing import Any

from django.db.models.query import QuerySet
from django.http.response import HttpResponse as HttpResponse
from django.urls import reverse
from guardian.shortcuts import assign_perm
from apps.core.permissions import EntryPermissions

from apps.core.utils import permission_denied_view
from apps.core.views.base_views import BaseGetModalFormView, BaseGetModalView
from apps.core.views.crud_base_views import (
    BaseCreateView,
    BaseDeleteView,
    BaseListView,
    BaseUpdateView,
)
from apps.core.views.mixins import WorkspaceRequiredMixin, WorkspaceTeamRequiredMixin
from apps.core.views.service_layer_mixins import (
    HtmxRowResponseMixin,
    HtmxTableServiceMixin,
)
from apps.remittance.services import (
    calculate_due_amount,
    calculate_paid_amount,
    update_remittance,
)
from apps.teams.constants import TeamMemberRole

from ..constants import CONTEXT_OBJECT_NAME, EntryStatus, EntryType
from ..forms import (
    BaseImportEntryForm,
    CreateWorkspaceTeamEntryForm,
    UpdateWorkspaceTeamEntryForm,
)
from ..models import Entry
from ..selectors import get_entries, get_entry
from ..services import EntryService
from ..utils import (
    can_add_workspace_team_entry,
    can_delete_workspace_team_entry,
    can_update_workspace_team_entry,
    can_update_other_submitters_entry,
)
from .base_views import (
    BaseEntryBulkCreateView,
    TeamLevelEntryView,
    BaseEntryBulkDeleteView,
    BaseEntryBulkUpdateView,
)
from .mixins import (
    EntryFormMixin,
    EntryRequiredMixin,
    WorkspaceLevelEntryFiltering,
    TeamLevelEntryFiltering,
)
from apps.entries.utils import can_view_total_workspace_teams_entries
from ..validators import TeamEntryValidator
from apps.workspaces.selectors import (
    get_workspace_team_member_by_workspace_team_and_org_member,
)


class WorkspaceEntryListView(
    WorkspaceRequiredMixin,
    TeamLevelEntryView,
    WorkspaceLevelEntryFiltering,
    BaseListView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/layouts/base_entry_content_layout.html"
    optional_htmx_template_name = "entries/partials/table.html"
    template_name = "entries/workspace_level_entry_index.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_view_total_workspace_teams_entries(request.user, self.workspace):
            return permission_denied_view(
                request, "You do not have permission to view this workspace's entries."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
            annotate_attachment_count=True,
            statuses=[self.request.GET.get("status")]
            if self.request.GET.get("status")
            else [EntryStatus.REVIEWED],
            type_filter=self.request.GET.get("type"),
            workspace_team_id=self.request.GET.get("team"),
            search=self.request.GET.get("search"),
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "workspace_lvl_entries"
        return context


class WorkspaceTeamEntryListView(
    WorkspaceTeamRequiredMixin,
    TeamLevelEntryView,
    TeamLevelEntryFiltering,
    BaseListView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/layouts/base_entry_content_layout.html"
    optional_htmx_template_name = "entries/partials/table.html"
    template_name = "entries/team_level_entry_index_for_review.html"
    secondary_template_name = "entries/team_level_entry_index_for_submitters.html"

    def get_template_names(self):
        if self.workspace_team_role == TeamMemberRole.SUBMITTER:
            return [self.secondary_template_name]
        return super().get_template_names()

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
            statuses=[self.request.GET.get("status")]
            if self.request.GET.get("status")
            else [EntryStatus.PENDING],
            type_filter=self.request.GET.get("type"),
            search=self.request.GET.get("search"),
        )


class WorkspaceTeamEntryCreateView(
    WorkspaceTeamRequiredMixin,
    TeamLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    TeamLevelEntryFiltering,
    HtmxTableServiceMixin,
    BaseCreateView,
):
    model = Entry
    form_class = CreateWorkspaceTeamEntryForm
    modal_template_name = "entries/components/create_modal.html"
    table_template_name = "entries/layouts/base_entry_content_layout.html"
    context_object_name = CONTEXT_OBJECT_NAME

    def dispatch(self, request, *args, **kwargs):
        if not can_add_workspace_team_entry(request.user, self.workspace_team):
            return permission_denied_view(
                request,
                "You do not have permission to add an entry to this workspace team.",
            )
        return super().dispatch(request, *args, **kwargs)

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
            statuses=[self.request.GET.get("status")]
            if self.request.GET.get("status")
            else [EntryStatus.PENDING],
            type_filter=self.request.GET.get("type"),
            search=self.request.GET.get("search"),
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
        entry = EntryService.create_entry_with_attachments(
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
            submitted_by_team_member=self.workspace_team_member,
            user=self.request.user,
            request=self.request,
        )
        # So ,only the submitter can edit the entry (except org admins,TC, workspace admins, operations reviewer) # dedicated to prevent other submitters from editing the entry
        assign_perm(
            EntryPermissions.CHANGE_OTHER_SUBMITTERS_ENTRY, self.request.user, entry
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

    def dispatch(self, request, *args, **kwargs):
        # general permission checking if the user has the permission to update the workspace team entry....
        if not can_update_workspace_team_entry(request.user, self.workspace_team):
            return permission_denied_view(
                request, "You do not have permission to update this entry."
            )
        # permission checking if the user has the permission to update other submitters entry....
        if not can_update_other_submitters_entry(
            request.user, self.org_member, self.entry, self.workspace_team
        ):
            return permission_denied_view(
                request, "You cannot edit other submitters entries."
            )
        return super().dispatch(request, *args, **kwargs)

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

        if self.entry.status == EntryStatus.PENDING:
            EntryService.update_entry_user_inputs(
                entry=self.entry,
                organization=self.organization,
                amount=form.cleaned_data["amount"],
                occurred_at=form.cleaned_data["occurred_at"],
                description=form.cleaned_data["description"],
                currency=form.cleaned_data["currency"],
                attachments=form.cleaned_data["attachment_files"],
                replace_attachments=form.cleaned_data["replace_attachments"],
                user=self.request.user,
                request=self.request,
            )

        # If the status has changed, update the status
        if self.entry.status != form.cleaned_data["status"]:
            EntryService.update_entry_status(
                entry=self.entry,
                status=form.cleaned_data["status"],
                last_status_modified_by=self.org_member,
                status_note=form.cleaned_data["status_note"],
            )


class WorkspaceTeamEntryDeleteView(
    WorkspaceTeamRequiredMixin,
    EntryRequiredMixin,
    TeamLevelEntryView,
    TeamLevelEntryFiltering,
    HtmxTableServiceMixin,
    BaseDeleteView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/layouts/base_entry_content_layout.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_delete_workspace_team_entry(request.user, self.workspace_team):
            return permission_denied_view(
                request, "You do not have permission to delete this entry."
            )
        return super().dispatch(request, *args, **kwargs)

    # Overriding get_object for a tighter fetch!
    # Entries can't be deleted once their status has been changed.
    # The normal `get_object` just grabs it by PK. This means we *could* fetch
    # an entry that exists but is ultimately undeletable due to rules.
    # While not a fatal error (it just won't delete), it's a bit messy.
    #
    # we make sure we're *only* trying to delete entries that strictly match
    # It's an indirect fix that just makes things cleaner.
    def get_object(self):
        return get_entry(
            pk=self.kwargs["pk"]
        )

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
            statuses=[self.request.GET.get("status")]
            if self.request.GET.get("status")
            else [EntryStatus.PENDING],
            type_filter=self.request.GET.get("type"),
            search=self.request.GET.get("search"),
        )

    def perform_service(self, form):
        EntryService.delete_entry(entry=self.entry, user=self.request.user, request=self.request)


class WorkspaceEntryBulkDeleteView(
    WorkspaceRequiredMixin,
    TeamLevelEntryView,
    WorkspaceLevelEntryFiltering,
    BaseGetModalView,
    BaseEntryBulkDeleteView,
):
    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
            statuses=[EntryStatus.PENDING],
        )

    def get_response_queryset(self):
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
            annotate_attachment_count=True,
            statuses=[EntryStatus.REVIEWED],
        )

    def validate_entry(self, entry):
        # Valid if status is pending and has never been modified
        return (
            entry.status == EntryStatus.PENDING
            and not entry.status_last_updated_at
            and not entry.last_status_modified_by
        )

    def get_post_url(self) -> str:
        return reverse(
            "workspace_entry_bulk_delete",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
            },
        )

    def get_modal_title(self) -> str:
        return ""


class WorkspaceEntryBulkUpdateView(
    WorkspaceRequiredMixin,
    TeamLevelEntryView,
    WorkspaceLevelEntryFiltering,
    BaseGetModalView,
    BaseEntryBulkUpdateView,
):
    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
        )

    def get_response_queryset(self):
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            entry_types=[
                EntryType.INCOME,
                EntryType.DISBURSEMENT,
                EntryType.REMITTANCE,
            ],
            annotate_attachment_count=True,
            statuses=[EntryStatus.REVIEWED],
        )

    def validate_entry(self, entry):
        try:
            workspace_team = entry.workspace_team
            workspace_team_member = (
                get_workspace_team_member_by_workspace_team_and_org_member(
                    workspace_team=workspace_team, org_member=self.org_member
                )
            )
            workspace_team_role = (
                workspace_team_member.role if workspace_team_member else None
            )
            validator = TeamEntryValidator(
                organization=self.organization,
                workspace=self.workspace,
                workspace_team=workspace_team,
                workspace_team_role=workspace_team_role,
                is_org_admin=self.is_org_admin,
                is_workspace_admin=self.is_workspace_admin,
                is_operation_reviewer=self.is_operation_reviewer,
                is_team_coordinator=entry.workspace_team.team.team_coordinator
                == self.org_member,
            )
            validator.validate_entry_update(entry, self.new_status)
        except Exception:
            return False
        return True

    def get_post_url(self) -> str:
        return reverse(
            "workspace_entry_bulk_update",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
            },
        )

    def get_modal_title(self) -> str:
        return ""


class WorkspaceTeamEntryBulkDeleteView(
    WorkspaceTeamRequiredMixin,
    TeamLevelEntryView,
    TeamLevelEntryFiltering,
    BaseGetModalView,
    BaseEntryBulkDeleteView,
):
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
            statuses=[EntryStatus.PENDING],
        )

    def get_response_queryset(self):
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
            statuses=[EntryStatus.PENDING],
        )

    def validate_entry(self, entry):
        # Valid if status is pending and has never been modified
        return (
            entry.status == EntryStatus.PENDING
            and not entry.status_last_updated_at
            and not entry.last_status_modified_by
        )

    def get_post_url(self) -> str:
        return reverse(
            "workspace_team_entry_bulk_delete",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "workspace_team_id": self.workspace_team.pk,
            },
        )

    def get_modal_title(self) -> str:
        return ""


class WorkspaceTeamEntryBulkUpdateView(
    WorkspaceTeamRequiredMixin,
    TeamLevelEntryView,
    TeamLevelEntryFiltering,
    BaseGetModalView,
    BaseEntryBulkUpdateView,
):
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
        )

    def get_response_queryset(self):
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
            statuses=[EntryStatus.PENDING],
        )

    def validate_entry(self, entry):
        try:
            validator = TeamEntryValidator(
                organization=self.organization,
                workspace=self.workspace,
                workspace_team=self.workspace_team,
                workspace_team_role=self.workspace_team_role,
                is_org_admin=self.is_org_admin,
                is_workspace_admin=self.is_workspace_admin,
                is_operation_reviewer=self.is_operation_reviewer,
                is_team_coordinator=self.is_team_coordinator,
            )
            validator.validate_entry_update(entry, self.new_status)
        except Exception:
            return False
        return True

    def get_post_url(self) -> str:
        return reverse(
            "workspace_team_entry_bulk_update",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "workspace_team_id": self.workspace_team.pk,
            },
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # At Team level, Approved status shouldn't be accessed
        context["modal_status_options"] = [
            (value, label)
            for value, label in EntryStatus.choices
            if value != EntryStatus.APPROVED
        ]
        return context

    def get_modal_title(self) -> str:
        return ""


class WorkspaceTeamEntryBulkCreateView(
    WorkspaceTeamRequiredMixin,
    TeamLevelEntryView,
    TeamLevelEntryFiltering,
    BaseGetModalFormView,
    BaseEntryBulkCreateView,
):
    form_class = BaseImportEntryForm
    modal_template_name = "entries/components/bulk_create_modal.html"
    entry_type_to_create = None

    def get_response_queryset(self):
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
            statuses=[EntryStatus.PENDING],
        )

    def get_post_url(self) -> str:
        return reverse(
            "workspace_team_entry_bulk_create",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "workspace_team_id": self.workspace_team.pk,
            },
        )

    def perform_post_action(self, entries: list[Entry]):
        remittance = self.workspace_team.remittance
        # After delete, both due/paid amounts might change
        remittance.due_amount = calculate_due_amount(workspace_team=self.workspace_team)
        remittance.paid_amount = calculate_paid_amount(
            workspace_team=self.workspace_team
        )
        update_remittance(remittance=remittance)
