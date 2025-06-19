from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Subquery
from django.shortcuts import get_object_or_404, render
from typing import Any

from .models import Entry
from apps.organizations.models import Organization, OrganizationMember
from apps.teams.models import TeamMember
from apps.core.constants import PAGINATION_SIZE
from django.contrib.contenttypes.models import ContentType
from .constants import EntryType, EntryStatus
from .forms import OrganizationExpenseEntryForm
from .services import create_org_expense_entry, get_org_expense_stats
from apps.organizations.selectors import get_user_org_membership
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import HttpResponse
from .selectors import get_org_expenses, get_total_org_expenses, get_this_month_org_expenses, get_average_monthly_org_expenses, get_last_month_org_expenses
from django.core.paginator import Paginator
from apps.core.utils import percent_change


class OrganizationExpenseListView(LoginRequiredMixin, ListView):
    model = Entry
    template_name = "entries/index.html"
    context_object_name = "entries"
    paginate_by = PAGINATION_SIZE

    def dispatch(self, request, *args, **kwargs):
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_org_expenses(self.organization)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["stats"] = get_org_expense_stats(self.organization)
        return context

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
        form = OrganizationExpenseEntryForm()
        context = {"form": form, "organization": self.organization}
        return render(request, "entries/components/create_org_exp_modal.html", context=context)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["org_member"] = self.org_member
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_oob"] = True
        context["messages"] = messages.get_messages(self.request)
        return context
    
    def form_valid(self, form):
        create_org_expense_entry(
            org_member=self.org_member,
            amount=form.cleaned_data["amount"],
            description=form.cleaned_data["description"]
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
        context = self.get_context_data()
        org_exp_entries = get_org_expenses(self.organization)
        paginator = Paginator(org_exp_entries, PAGINATION_SIZE)
        page_obj = paginator.get_page(1)
        # Merge the existing context dict with the new one
        context.update(
            {
                "page_obj": page_obj,
                "paginator": paginator,
                "entries": page_obj.object_list,
                "is_paginated": paginator.num_pages > 1,
            }
        )
        context["stats"] = get_org_expense_stats(self.organization)
        stat_overview_html = render_to_string("components/stat_section.html", context=context, request=self.request)
        table_html = render_to_string("entries/partials/table.html", context=context, request=self.request)
        message_html = render_to_string("includes/message.html", context=context, request=self.request)
        response = HttpResponse(f"{message_html}{table_html}{stat_overview_html}")
        response["HX-trigger"] = "success"
        return response
    
    def _render_htmx_error_response(self, form):
        context = self.get_context_data()
        context["form"] = form
        context["organization"] = self.organization
        message_html = render_to_string(
            "includes/message.html", context=context, request=self.request
        )
        modal_html = render_to_string(
            "entries/components/create_org_exp_modal.html",
            context=context,
            request=self.request,
        )
        return HttpResponse(f"{message_html} {modal_html}")
