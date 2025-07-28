from typing import Any
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http.response import HttpResponse as HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse

from apps.core.views.base_views import BaseGetModalFormView
from ..constants import CONTEXT_OBJECT_NAME, EntryType
from ..selectors import get_entries
from ..services import get_org_expense_stats
from apps.core.views.mixins import (
    OrganizationRequiredMixin,
)
from .mixins import (
    EntryFormMixin,
    # OrganizationRequiredMixin,
    # WorkspaceRequiredMixin,
    # OrganizationContextMixin,
    # WorkspaceContextMixin,
)
from .base_views import (
    OrganizationLevelEntryView,
)
from ..forms import (
    CreateOrganizationExpenseEntryForm,
    # CreateWorkspaceExpenseEntryForm,
    # UpdateOrganizationExpenseEntryForm,
    # UpdateWorkspaceExpenseEntryForm,
)
from apps.core.permissions import OrganizationPermissions, WorkspacePermissions
from apps.core.utils import permission_denied_view
from apps.core.views.crud_base_views import (
    BaseCreateView,
    BaseListView,
)
from ..models import Entry


class OrganizationExpenseListView(
    OrganizationRequiredMixin,
    OrganizationLevelEntryView,
    BaseListView,
):
    model = Entry
    context_object_name = CONTEXT_OBJECT_NAME
    table_template_name = "entries/partials/table.html"
    template_name = "entries/index.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(
            OrganizationPermissions.VIEW_ORG_ENTRY, self.organization
        ):
            return permission_denied_view(
                request,
                "You do not have permission to view organization expenses.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        return Entry.objects.filter(
            organization = self.organization,
            entry_type = EntryType.ORG_EXP
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if not self.request.htmx:
            pass
            # context["stats"] = get_org_expense_stats(self.organization)
        return context


class OrganizationExpenseCreateView(
    OrganizationRequiredMixin,
    OrganizationLevelEntryView,
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
            entry_type = EntryType.ORG_EXP
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

        try:
            create_entry_with_attachments(
                amount =form.cleaned_data["amount"],
                occurred_at = form.cleaned_data["occurred_at"],
                description =form.cleaned_data["description"],
                attachments = form.cleaned_data["attachment_files"],
                entry_type = EntryType.ORG_EXP,
                organization = self.organization,
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

        # stat_context = {
        #     **base_context,
        #     "stats": get_org_expense_stats(self.organization),
        # }

        from apps.core.utils import get_paginated_context

        org_exp_entries = self.get_queryset()
        table_context = get_paginated_context(
            queryset=org_exp_entries,
            context=base_context,
            object_name=CONTEXT_OBJECT_NAME,
        )

        # stat_overview_html = render_to_string(
        #     "components/stat_section.html", context=stat_context, request=self.request
        # )
        table_html = render_to_string(
            "entries/partials/table.html", context=table_context, request=self.request
        )
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        response = HttpResponse(f"{message_html}{table_html}")
        response["HX-trigger"] = "success"
        return response