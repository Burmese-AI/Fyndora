from typing import Any
from django.db.models.query import QuerySet
from django.http.response import HttpResponse as HttpResponse
from django.urls import reverse
from ..selectors import get_entries

from apps.core.views.base_views import BaseGetModalFormView
from ..constants import CONTEXT_OBJECT_NAME, EntryStatus, EntryType
from apps.core.views.mixins import (
    WorkspaceRequiredMixin,
)
from .mixins import (
    EntryFormMixin,
    EntryRequiredMixin,
)
from .base_views import (
    WorkspaceLevelEntryView,
)
from ..forms import (
    CreateOrganizationExpenseEntryForm,
    UpdateOrganizationExpenseEntryForm,
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
from ..utils import can_add_workspace_expense, can_update_workspace_expense, can_delete_workspace_expense


class WorkspaceExpenseListView(
    WorkspaceRequiredMixin,
    WorkspaceLevelEntryView,
    BaseListView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"
    template_name = "entries/workspace_expense_index.html"

    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            entry_types=[EntryType.WORKSPACE_EXP],
            annotate_attachment_count=True,
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:

        context = super().get_context_data(**kwargs)
        context["view"] = "entries"
        context["permissions"] = {
            "can_add_workspace_expense": can_add_workspace_expense(self.request.user, self.workspace),
        }
        return context


class WorkspaceExpenseCreateView(
    WorkspaceRequiredMixin,
    WorkspaceLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    HtmxTableServiceMixin,
    BaseCreateView,
):
    model = Entry
    form_class = CreateOrganizationExpenseEntryForm
    modal_template_name = "entries/components/create_modal.html"
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_add_workspace_expense(request.user, self.workspace):
            return permission_denied_view(
                request,
                "You do not have permission to add workspace expenses.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            entry_types=[EntryType.WORKSPACE_EXP],
            annotate_attachment_count=True,
        )

    def get_modal_title(self) -> str:
        return "Workspace Expense"

    def get_post_url(self) -> str:
        return reverse(
            "workspace_expense_create",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
            },
        )

    def perform_service(self, form):
        from ..services import create_entry_with_attachments

        create_entry_with_attachments(
            amount=form.cleaned_data["amount"],
            occurred_at=form.cleaned_data["occurred_at"],
            description=form.cleaned_data["description"],
            attachments=form.cleaned_data["attachment_files"],
            entry_type=EntryType.WORKSPACE_EXP,
            organization=self.organization,
            workspace=self.workspace,
            currency=form.cleaned_data["currency"],
            submitted_by_org_member=self.org_member,
        )


class WorkspaceExpenseUpdateView(
    WorkspaceRequiredMixin,
    EntryRequiredMixin,
    WorkspaceLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    HtmxRowResponseMixin,
    BaseUpdateView,
):
    model = Entry
    form_class = UpdateOrganizationExpenseEntryForm
    modal_template_name = "entries/components/update_modal.html"
    row_template_name = "entries/partials/row.html",

    def dispatch(self, request, *args, **kwargs):
        if not can_update_workspace_expense(request.user, self.workspace):
            return permission_denied_view(
                request,
                "You do not have permission to update workspace expenses.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Entry.objects.filter(
            organization=self.organization,
            workspace=self.workspace,
            entry_type=EntryType.WORKSPACE_EXP,
            entry_id=self.kwargs["pk"],
        )

    def get_modal_title(self) -> str:
        return "Workspace Expense"

    def get_post_url(self) -> str:
        return reverse(
            "workspace_expense_update",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
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


class WorkspaceExpenseDeleteView(
    WorkspaceRequiredMixin,
    EntryRequiredMixin,
    WorkspaceLevelEntryView,
    HtmxTableServiceMixin,
    BaseDeleteView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_delete_workspace_expense(request.user, self.workspace):
            return permission_denied_view(
                request,
                "You do not have permission to delete workspace expenses.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_entries(
            organization=self.organization,
            workspace=self.workspace,
            entry_types=[EntryType.WORKSPACE_EXP],
            annotate_attachment_count=True,
        )

    def perform_service(self, form):
        from ..services import delete_entry

        delete_entry(self.entry)
