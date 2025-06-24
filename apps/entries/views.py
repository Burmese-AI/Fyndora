from typing import Any

from django.db.models.query import QuerySet
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import HttpRequest, HttpResponse

from apps.organizations.models import Organization
from apps.core.constants import PAGINATION_SIZE
from apps.organizations.selectors import get_user_org_membership
from apps.core.utils import get_paginated_context
from .models import Entry
from .constants import CONTEXT_OBJECT_NAME
from .forms import OrganizationExpenseEntryForm
from .services import (
    create_org_expense_entry_with_attachments,
    update_org_expense_entry_with_attachments,
    get_org_expense_stats,
)
from .selectors import get_org_expenses


class OrganizationExpenseListView(LoginRequiredMixin, ListView):
    model = Entry
    template_name = "entries/index.html"
    context_object_name = CONTEXT_OBJECT_NAME
    paginate_by = PAGINATION_SIZE

    def dispatch(self, request, *args, **kwargs):
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_org_expenses(self.organization)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # When rendering partially, these contexts are not required
        context["organization"] = self.organization
        if not self.request.htmx:
            context["stats"] = get_org_expense_stats(self.organization)
        return context

    def render_to_response(
        self, context: dict[str, Any], **response_kwargs: Any
    ) -> HttpResponse:
        if self.request.htmx:
            return render(self.request, "entries/partials/table.html", context)
        return super().render_to_response(context, **response_kwargs)


class OrganizationExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Entry
    form_class = OrganizationExpenseEntryForm

    def __init__(self):
        self.organization = None

    def dispatch(self, request, *args, **kwargs):
        # Get ORG ID from URL
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        self.org_member = get_user_org_membership(self.request.user, self.organization)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        context = {"form": form, "organization": self.organization}
        return render(
            request, "entries/components/create_org_exp_modal.html", context=context
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["org_member"] = self.org_member
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            context["is_oob"] = True
        return context

    def form_valid(self, form):
        # Create org exp entry with provided attachments
        create_org_expense_entry_with_attachments(
            org_member=self.org_member,
            amount=form.cleaned_data["amount"],
            description=form.cleaned_data["description"],
            attachments=form.cleaned_data["attachment_files"],
        )
        messages.success(self.request, "Expense entry submitted successfully")
        if self.request.htmx:
            return self._render_htmx_success_response()
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Expense entry submission failed")
        if self.request.htmx:
            return self._render_htmx_error_response(form)
        return super().form_invalid(form)

    def _render_htmx_success_response(self):
        base_context = self.get_context_data()

        stat_context = {
            **base_context,
            "stats": get_org_expense_stats(self.organization),
        }

        org_exp_entries = get_org_expenses(self.organization)
        table_context = get_paginated_context(
            queryset=org_exp_entries,
            context=base_context,
            object_name=CONTEXT_OBJECT_NAME,
        )
        table_context["organization"] = self.organization

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

    def _render_htmx_error_response(self, form):
        base_context = self.get_context_data()
        modal_context = {
            **base_context,
            "form": form,
            "organization": self.organization,
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


class OrganizationExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Entry
    form_class = OrganizationExpenseEntryForm

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        organization_id = self.kwargs["organization_id"]
        org_exp_entry_id = self.kwargs["pk"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        self.org_member = get_user_org_membership(self.request.user, self.organization)
        self.org_exp_entry = get_object_or_404(Entry, pk=org_exp_entry_id)
        self.attachments = self.org_exp_entry.attachments.all()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        return get_org_expenses(self.organization)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["org_member"] = self.org_member
        kwargs["instance"] = self.org_exp_entry
        kwargs["is_update"] = True
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            context["is_oob"] = True
        return context

    def get(self, request, *args, **kwargs):
        form = self.get_form()

        context = {
            "form": form,
            "organization": self.organization,
            "entry": self.org_exp_entry,
            "attachments": self.attachments,
        }
        return render(
            request, "entries/components/update_org_exp_modal.html", context=context
        )

    def form_valid(self, form):
        # Update org exp entry along with attachements if provided
        update_org_expense_entry_with_attachments(
            entry=self.org_exp_entry,
            amount=form.cleaned_data["amount"],
            description=form.cleaned_data["description"],
            attachments=form.cleaned_data["attachment_files"],
        )
        messages.success(self.request, "Expense entry updated successfully")
        if self.request.htmx:
            return self._render_htmx_success_response()
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Expense entry submission failed")
        if self.request.htmx:
            return self._render_htmx_error_response(form)
        return super().form_invalid(form)

    def _render_htmx_success_response(self):
        base_context = self.get_context_data()

        stat_context = {
            **base_context,
            "stats": get_org_expense_stats(self.organization),
        }

        row_context = {
            **base_context,
            "organization": self.organization,
            "entry": self.org_exp_entry,
        }

        stat_overview_html = render_to_string(
            "components/stat_section.html", context=stat_context, request=self.request
        )

        row_html = render_to_string(
            "entries/partials/row.html", context=row_context, request=self.request
        )

        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )
        response = HttpResponse(f"{message_html}{row_html}{stat_overview_html}")
        response["HX-trigger"] = "success"
        return response

    def _render_htmx_error_response(self, form):
        base_context = self.get_context_data()
        modal_context = {
            **base_context,
            "form": form,
            "organization": self.organization,
            "entry": self.org_exp_entry,
            "attachments": self.attachments,
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
