from typing import Any
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http.response import HttpResponse as HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse
from ..constants import CONTEXT_OBJECT_NAME, EntryType
from ..selectors import get_entries
from ..services import get_org_expense_stats
from .mixins import (
    OrganizationRequiredMixin,
    WorkspaceRequiredMixin,
    OrganizationContextMixin,
    WorkspaceContextMixin,
)
from .base_views import (
    BaseEntryListView,
    BaseEntryCreateView,
    BaseEntryUpdateView,
)


class OrganizationExpenseListView(
    LoginRequiredMixin,
    OrganizationRequiredMixin,
    OrganizationContextMixin,
    BaseEntryListView,
):
    template_name = "entries/index.html"

    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            organization=self.organization, entry_types=[EntryType.ORG_EXP]
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if not self.request.htmx:
            context["stats"] = get_org_expense_stats(self.organization)
        return context


class OrganizationExpenseCreateView(
    LoginRequiredMixin,
    OrganizationRequiredMixin,
    OrganizationContextMixin,
    BaseEntryCreateView,
):
    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            organization=self.organization, entry_types=[EntryType.ORG_EXP]
        )

    def get_modal_title(self) -> str:
        return "Organization Expense"

    def get_post_url(self) -> str:
        return reverse(
            "organization_expense_create",
            kwargs={"organization_id": self.organization.pk},
        )

    def form_valid(self, form):
        from ..services import create_entry_with_attachments
        from ..constants import EntryType

        create_entry_with_attachments(
            submitter=self.org_member,
            amount=form.cleaned_data["amount"],
            description=form.cleaned_data["description"],
            attachments=form.cleaned_data["attachment_files"],
            entry_type=EntryType.ORG_EXP,
        )
        messages.success(self.request, "Expense entry submitted successfully")
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        stat_context = {
            **base_context,
            "stats": get_org_expense_stats(self.organization),
        }

        from apps.core.utils import get_paginated_context

        org_exp_entries = self.get_queryset()
        table_context = get_paginated_context(
            queryset=org_exp_entries,
            context=base_context,
            object_name=CONTEXT_OBJECT_NAME,
        )

        stat_overview_html = render_to_string(
            "components/stat_section.html", context=stat_context, request=self.request
        )
        table_html = render_to_string(
            "entries/partials/table.html", context=table_context, request=self.request
        )
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        response = HttpResponse(f"{message_html}{table_html}{stat_overview_html}")
        response["HX-trigger"] = "success"
        return response


class OrganizationExpenseUpdateView(
    LoginRequiredMixin,
    OrganizationRequiredMixin,
    OrganizationContextMixin,
    BaseEntryUpdateView,
):
    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            organization=self.organization, entry_types=[EntryType.ORG_EXP]
        )

    def get_modal_title(self) -> str:
        return "Organization Expense"

    def get_post_url(self) -> str:
        return reverse(
            "organization_expense_update",
            kwargs={"organization_id": self.organization.pk, "pk": self.entry.pk},
        )

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        stat_context = {
            **base_context,
            "stats": get_org_expense_stats(self.organization),
        }

        stat_overview_html = render_to_string(
            "components/stat_section.html", context=stat_context, request=self.request
        )

        row_html = render_to_string(
            "entries/partials/row.html", context=base_context, request=self.request
        )

        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )

        # Added table tag to the response to fix the issue of the row not being rendered
        response = HttpResponse(
            f"{message_html}{stat_overview_html}<table>{row_html}</table>"
        )
        response["HX-trigger"] = "success"
        return response


class WorkspaceExpenseListView(
    LoginRequiredMixin,
    WorkspaceRequiredMixin,
    WorkspaceContextMixin,
    BaseEntryListView
):
    template_name = "entries/workspace_expense_index.html"

    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            workspace=self.workspace, entry_types=[EntryType.WORKSPACE_EXP]
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "entries"
        return context


class WorkspaceExpenseCreateView(
    LoginRequiredMixin,
    WorkspaceRequiredMixin,
    WorkspaceContextMixin,
    BaseEntryCreateView,
):
    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            workspace=self.workspace, entry_types=[EntryType.WORKSPACE_EXP]
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

        create_entry_with_attachments(
            submitter=self.org_member,
            amount=form.cleaned_data["amount"],
            description=form.cleaned_data["description"],
            attachments=form.cleaned_data["attachment_files"],
            entry_type=EntryType.WORKSPACE_EXP,
            workspace=self.workspace,
        )
        messages.success(self.request, "Expense entry submitted successfully")
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        from apps.core.utils import get_paginated_context

        workspace_exp_entries = self.get_queryset()
        table_context = get_paginated_context(
            queryset=workspace_exp_entries,
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
    LoginRequiredMixin,
    WorkspaceRequiredMixin,
    WorkspaceContextMixin,
    BaseEntryUpdateView
):
    def get_queryset(self) -> QuerySet[Any]:
        return get_entries(
            workspace=self.workspace, entry_types=[EntryType.WORKSPACE_EXP]
        )

    def get_modal_title(self) -> str:
        return "Workspace Expense"

    def get_post_url(self) -> str:
        return reverse(
            "workspace_expense_update",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "pk": self.entry.pk,
            },
        )
