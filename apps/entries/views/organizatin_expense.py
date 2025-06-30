from typing import Any
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.http.response import HttpResponse as HttpResponse
from django.views.generic import ListView, CreateView, UpdateView
from django.template.loader import render_to_string
from django.shortcuts import render
from django.contrib import messages
from apps.core.constants import PAGINATION_SIZE
from ..models import Entry
from ..constants import CONTEXT_OBJECT_NAME
from ..selectors import get_org_expenses
from ..services import get_org_expense_stats
from ..forms import BaseEntryForm, CreateEntryForm, UpdateEntryForm
from .base import (
    OrganizationRequiredMixin,
    HtmxOobResponseMixin,
    OrganizationMemberRequiredMixin,
    OrganizationExpenseEntryRequiredMixin,
    OrganizationContextMixin,
)


class BaseEntryFormMixin:
    form_class = BaseEntryForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["org_member"] = self.org_member
        return kwargs
    
class CreateEntryFormMixin(BaseEntryFormMixin):
    form_class = CreateEntryForm
    
class UpdateEntryFormMixin(BaseEntryFormMixin):
    form_class = UpdateEntryForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = getattr(
            self, "org_exp_entry", None
        )
        return kwargs


class OrganizationExpenseListView(
    LoginRequiredMixin, OrganizationRequiredMixin, OrganizationContextMixin, ListView
):
    model = Entry
    template_name = "entries/index.html"
    context_object_name = CONTEXT_OBJECT_NAME
    paginate_by = PAGINATION_SIZE

    def get_queryset(self) -> QuerySet[Any]:
        return get_org_expenses(self.organization)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if not self.request.htmx:
            context["stats"] = get_org_expense_stats(self.organization)
        return context

    def render_to_response(
        self, context: dict[str, Any], **response_kwargs: Any
    ) -> HttpResponse:
        if self.request.htmx:
            return render(self.request, "entries/partials/table.html", context)
        return super().render_to_response(context, **response_kwargs)


class OrganizationExpenseCreateView(
    LoginRequiredMixin,
    OrganizationMemberRequiredMixin,
    CreateEntryFormMixin,
    HtmxOobResponseMixin,
    OrganizationContextMixin,
    CreateView,
):
    modal_template = "entries/components/create_org_exp_modal.html"

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = None
        form = self.get_form()
        context = self.get_context_data()
        context["form"] = form
        context["is_oob"] = (
            False  # Overriding the default value from HtmxOobResponseMixin context data
        )
        return render(request, self.modal_template, context)

    def form_valid(self, form):
        from ..services import create_entry_with_attachments
        from ..constants import EntryType

        create_entry_with_attachments(
            submitter=self.org_member,
            amount=form.cleaned_data["amount"],
            description=form.cleaned_data["description"],
            attachments=form.cleaned_data["attachment_files"],
            entry_type=EntryType.ORG_EXP
        )
        messages.success(self.request, "Expense entry submitted successfully")
        return self._render_htmx_success_response()

    def form_invalid(self, form):
        messages.error(self.request, "Expense entry submission failed")
        return self._render_htmx_error_response(form)

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        stat_context = {
            **base_context,
            "stats": get_org_expense_stats(self.organization),
        }

        from apps.core.utils import get_paginated_context

        org_exp_entries = get_org_expenses(self.organization)
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

    def _render_htmx_error_response(self, form) -> HttpResponse:
        base_context = self.get_context_data()
        modal_context = {
            **base_context,
            "form": form,
        }

        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        modal_html = render_to_string(
            "entries/components/create_org_exp_modal.html",
            context=modal_context,
            request=self.request,
        )
        return HttpResponse(f"{message_html} {modal_html}")


class OrganizationExpenseUpdateView(
    LoginRequiredMixin,
    OrganizationExpenseEntryRequiredMixin,
    UpdateEntryFormMixin,
    HtmxOobResponseMixin,
    OrganizationContextMixin,
    UpdateView,
):
    modal_template = "entries/components/update_org_exp_modal.html"

    def get_queryset(self) -> QuerySet[Any]:
        return get_org_expenses(self.organization)

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        context = self.get_context_data()
        context["form"] = form
        context["is_oob"] = (
            False  # Overriding the default value from HtmxOobResponseMixin context data
        )
        return render(request, self.modal_template, context=context)

    def form_valid(self, form):
        # Update org exp entry along with attachements if provided
        from ..services import update_entry_with_attachments

        update_entry_with_attachments(
            entry=self.org_exp_entry,
            amount=form.cleaned_data["amount"],
            description=form.cleaned_data["description"],
            status=form.cleaned_data["status"],
            review_notes=form.cleaned_data["review_notes"],
            attachments=form.cleaned_data["attachment_files"],
            replace_attachments=form.cleaned_data["replace_attachments"],
        )

        messages.success(
            self.request, f"Expense entry {self.org_exp_entry.pk} updated successfully"
        )
        return self._render_htmx_success_response()

    def form_invalid(self, form):
        messages.error(self.request, "Expense entry submission failed")
        return self._render_htmx_error_response(form)

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
        response = HttpResponse(f"{message_html}{stat_overview_html}{row_html}")
        response["HX-trigger"] = "success"
        return response

    def _render_htmx_error_response(self, form) -> HttpResponse:
        base_context = self.get_context_data()
        modal_context = {
            **base_context,
            "form": form,
        }

        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        modal_html = render_to_string(
            "entries/components/update_org_exp_modal.html",
            context=modal_context,
            request=self.request,
        )
        return HttpResponse(f"{message_html} {modal_html}")
