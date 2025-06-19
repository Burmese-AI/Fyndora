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
        # Get content types
        org_member_type = ContentType.objects.get_for_model(OrganizationMember)
        team_member_type = ContentType.objects.get_for_model(TeamMember)

        # Subquery: IDs of Organization Members in this organization
        org_members_subquery = Subquery(
            OrganizationMember.objects.filter(organization=self.organization).values(
                "pk"
            )
        )

        # Subquery: IDs of TeamMembers whose OrganizationMember belongs to this org
        team_members_subquery = Subquery(
            TeamMember.objects.filter(
                organization_member__organization=self.organization
            ).values("pk")
        )

        # Main queryset filtering both submitter types
        return (
            Entry.objects.filter(
                Q(submitter_content_type=org_member_type)
                & Q(submitter_object_id__in=org_members_subquery)
                | Q(submitter_content_type=team_member_type)
                & Q(submitter_object_id__in=team_members_subquery)
            )
            .filter(entry_type=EntryType.WORKSPACE_EXP, status=EntryStatus.APPROVED)
            .select_related("submitter_content_type")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
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
        # org_exp_entries =
        message_html = render_to_string("includes/message.html", context=context, request=self.request)
        response = HttpResponse(f"{message_html}")
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
