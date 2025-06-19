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
from .services import create_org_expense_entry
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
        total = get_total_org_expenses(self.organization)
        this_month = get_this_month_org_expenses(self.organization)
        last_month = get_last_month_org_expenses(self.organization)
        avg_monthly = get_average_monthly_org_expenses(self.organization)

        context["stats"] = [
            {
                "title": "Total Expenses",
                "value": f"${total:,.0f}",
                "subtitle": percent_change(total, last_month),
                "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z"/></svg>'
            },
            {
                "title": "This Month’s Expenses",
                "value": f"${this_month:,.0f}",
                "subtitle": percent_change(this_month, last_month),
                "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-9-6h.008v.008H12v-.008ZM12 15h.008v.008H12V15Zm0 2.25h.008v.008H12v-.008ZM9.75 15h.008v.008H9.75V15Zm0 2.25h.008v.008H9.75v-.008ZM7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm6.75-4.5h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V15Zm0 2.25h.008v.008h-.008v-.008Zm2.25-4.5h.008v.008H16.5v-.008Zm0 2.25h.008v.008H16.5V15Z"/></svg>'
            },
            {
                "title": "Average Monthly Expense",
                "value": f"${avg_monthly:,.0f}",
                "subtitle": percent_change(this_month, avg_monthly),
                "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"/></svg>'
            },
        ]
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
        table_html = render_to_string("entries/partials/table.html", context=context, request=self.request)
        message_html = render_to_string("includes/message.html", context=context, request=self.request)
        response = HttpResponse(f"{message_html}{table_html}")
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
