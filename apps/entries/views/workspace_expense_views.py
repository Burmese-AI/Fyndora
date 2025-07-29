from typing import Any
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http.response import HttpResponse as HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse

from apps.core.views.base_views import BaseGetModalFormView
from ..constants import CONTEXT_OBJECT_NAME, EntryStatus, EntryType
from ..selectors import get_entries
from ..services import delete_entry, get_org_expense_stats
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
    WorkspaceRequiredMixin,
)
from .mixins import (
    EntryFormMixin,
    EntryRequiredMixin,
)
from .base_views import (
    OrganizationLevelEntryView,
    WorkspaceLevelEntryView,
)
from ..forms import (
    CreateOrganizationExpenseEntryForm,
    UpdateOrganizationExpenseEntryForm
    # CreateWorkspaceExpenseEntryForm,
    # UpdateOrganizationExpenseEntryForm,
    # UpdateWorkspaceExpenseEntryForm,
)
from apps.core.permissions import OrganizationPermissions, WorkspacePermissions
from apps.core.utils import permission_denied_view
from apps.core.views.crud_base_views import (
    BaseCreateView,
    BaseDeleteView,
    BaseListView,
    BaseUpdateView,
)
from ..models import Entry


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
        return Entry.objects.filter(
            organization = self.organization,
            workspace = self.workspace,
            entry_type = EntryType.WORKSPACE_EXP
        )
        
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "entries"
        return context
    
class WorkspaceExpenseCreateView(
    WorkspaceRequiredMixin,
    WorkspaceLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    BaseCreateView,
):
    model = Entry
    form_class = CreateOrganizationExpenseEntryForm
    modal_template_name = "entries/components/create_modal.html"
    
    def get_queryset(self):
        return Entry.objects.filter(
            organization = self.organization,
            workspace = self.workspace,
            entry_type = EntryType.WORKSPACE_EXP
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
        
    def form_valid(self, form):
        from ..services import create_entry_with_attachments
        from ..constants import EntryType

        try:
            create_entry_with_attachments(
                amount =form.cleaned_data["amount"],
                occurred_at = form.cleaned_data["occurred_at"],
                description =form.cleaned_data["description"],
                attachments = form.cleaned_data["attachment_files"],
                entry_type = EntryType.WORKSPACE_EXP,
                organization = self.organization,
                workspace = self.workspace,
                currency = form.cleaned_data["currency"],
                submitted_by_org_member = self.org_member
            )
        except Exception as e:
            messages.error(self.request, f"Expense entry submission failed: {e}")
            return self._render_htmx_error_response(form)
        
        messages.success(self.request, "Expense entry submitted successfully")
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        from apps.core.utils import get_paginated_context

        org_exp_entries = self.get_queryset()
        table_context = get_paginated_context(
            queryset=org_exp_entries,
            context=base_context,
            object_name=CONTEXT_OBJECT_NAME,
        )
        
        table_html = render_to_string(
            "entries/partials/table.html", context=table_context, request=self.request
        )
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        response = HttpResponse(f"{message_html}{table_html}")
        response["HX-trigger"] = "success"
        return response
 
 
class WorkspaceExpenseUpdateView(
    WorkspaceRequiredMixin,
    EntryRequiredMixin,
    WorkspaceLevelEntryView,
    BaseGetModalFormView,
    EntryFormMixin,
    BaseUpdateView
):
    model = Entry
    form_class = UpdateOrganizationExpenseEntryForm
    modal_template_name = "entries/components/update_modal.html"
    
    def get_queryset(self):
        return Entry.objects.filter(
            organization = self.organization,
            workspace = self.workspace,
            entry_type = EntryType.WORKSPACE_EXP,
            entry_id = self.kwargs["pk"]
        )
    
    def get_modal_title(self) -> str:
        return "Workspace Expense"
    
    def get_post_url(self) -> str:
        return reverse(
            "workspace_expense_update",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "pk": self.instance.pk
            },
        )
        
    def form_valid(self, form):
        
        try:
            from ..services import update_entry_status, update_entry_user_inputs
            if self.entry.status == EntryStatus.PENDING:
                update_entry_user_inputs(
                    entry = self.entry,
                    organization = self.organization,
                    amount = form.cleaned_data["amount"],
                    occurred_at = form.cleaned_data["occurred_at"],
                    description = form.cleaned_data["description"],
                    currency = form.cleaned_data["currency"],
                    attachments = form.cleaned_data["attachment_files"],
                    replace_attachments = True,
                )
            
            # If the status has changed, update the status
            if self.entry.status != form.cleaned_data["status"]:
                update_entry_status(
                    entry = self.entry,
                    status = form.cleaned_data["status"],
                    last_status_modified_by = self.org_member,
                    status_note = form.cleaned_data["status_note"],
                )
            
        except Exception as e:
            messages.error(self.request, f"Expense entry update failed: {e}")
            return self._render_htmx_error_response(form)
        
        messages.success(self.request, "Expense entry updated successfully")
        return self._render_htmx_success_response()
    
    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        row_html = render_to_string(
            "entries/partials/row.html", context=base_context, request=self.request
        )

        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )

        # Added table tag to the response to fix the issue of the row not being rendered
        response = HttpResponse(
            f"{message_html}<table>{row_html}</table>"
        )
        response["HX-trigger"] = "success"
        return response
  
  
class WorkspaceExpenseDeleteView(
    WorkspaceRequiredMixin,
    EntryRequiredMixin,
    WorkspaceLevelEntryView,
    BaseDeleteView
):
    model = Entry

    def get_queryset(self):
        return Entry.objects.filter(
            organization = self.organization,
            workspace = self.workspace,
            entry_type = EntryType.WORKSPACE_EXP,
        )
        
    def form_valid(self, form):
        from ..services import delete_entry
        try:
            delete_entry(self.entry)
        except Exception as e:
            messages.error(self.request, f"Expense entry deletion failed: {e}")
            return self._render_htmx_error_response()
        messages.success(self.request, "Expense entry deleted successfully")
        return self._render_htmx_success_response()
    
    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()
        
        from apps.core.utils import get_paginated_context

        org_exp_entries = self.get_queryset()

        table_context = get_paginated_context(
            queryset=org_exp_entries,
            context=base_context,
            object_name=CONTEXT_OBJECT_NAME,
        )
        table_html = render_to_string(
            "entries/partials/table.html", context=table_context, request=self.request
        )
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        response = HttpResponse(f"{message_html}{table_html}")
        return response