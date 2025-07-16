from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from .models import Invitation
from .forms import InvitationCreateForm
from apps.organizations.models import Organization
from .services import (
    create_invitation,
    accept_invitation,
    verify_invitation_for_acceptance,
)
from .selectors import get_organization_member_by_user_and_organization
from apps.core.constants import PAGINATION_SIZE
from typing import Any
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.core.paginator import Paginator
from apps.core.permissions import OrganizationPermissions
from apps.core.utils import permission_denied_view

class InvitationListView(LoginRequiredMixin, ListView):
    model = Invitation
    template_name = "invitations/index.html"
    context_object_name = "invitations"
    paginate_by = PAGINATION_SIZE

    def dispatch(self, request, *args, **kwargs):
        # Get ORG ID from URL
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Invitation.objects.filter(organization=self.organization)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "invitations"
        context["organization"] = self.organization
        return context

    def render_to_response(self, context: dict[str, Any], **response_kwargs: Any):
        if self.request.htmx:
            return render(self.request, "invitations/partials/table.html", context)
        return super().render_to_response(context, **response_kwargs)


class InvitationCreateView(LoginRequiredMixin, CreateView):
    model = Invitation
    form_class = InvitationCreateForm

    def __init__(self):
        self.organization = None

    def dispatch(self, request, *args, **kwargs):
        # Get ORG ID from URL
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)

        if not self.request.user.has_perm(OrganizationPermissions.INVITE_ORG_MEMBER, self.organization):
            return permission_denied_view(
            request,
            "You do not have permission to invite org members to this organization.",
        )

        return super().dispatch(request, *args, **kwargs)
    

    def get(self, request, *args, **kwargs):
        form = InvitationCreateForm()
        context = {"form": form, "organization": self.organization}
        return render(
            request, "invitations/components/create_modal.html", context=context
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass additional data to the kwargs which Form class will receive when initializing
        kwargs["organization"] = self.organization
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["is_oob"] = True
        context["messages"] = messages.get_messages(self.request)
        return context

    @transaction.atomic
    def form_valid(self, form):
        create_invitation(
            email=form.cleaned_data["email"],
            expired_at=form.cleaned_data["expired_at"],
            organization=self.organization,
            invited_by=get_organization_member_by_user_and_organization(
                user=self.request.user, organization=self.organization
            ),
        )
        # For success, Send messages templates and invitation table with enabled OOB
        messages.success(self.request, "Invitation sent successfully")
        if self.request.htmx:
            return self._render_htmx_success_response()

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Failed to send invitation")
        if self.request.htmx:
            return self._render_htmx_error_response(form)

        return super().form_invalid(form)

    def _render_htmx_success_response(self):
        context = self.get_context_data()
        invitations = Invitation.objects.filter(organization=self.organization)
        paginator = Paginator(invitations, PAGINATION_SIZE)
        page_obj = paginator.get_page(1)
        # Merge the existing context dict with the new one
        context.update(
            {
                "page_obj": page_obj,
                "paginator": paginator,
                "invitations": page_obj.object_list,
                "is_paginated": paginator.num_pages > 1,
            }
        )
        message_html = render_to_string(
            "includes/message.html", context=context, request=self.request
        )
        table_html = render_to_string(
            "invitations/partials/table.html", context=context, request=self.request
        )
        response = HttpResponse(f"{message_html} {table_html}")
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
            "invitations/components/create_modal.html",
            context=context,
            request=self.request,
        )
        return HttpResponse(f"{message_html} {modal_html}")

    def get_success_url(self):
        return reverse(
            "invitation_list",
            kwargs={"organization_id": self.kwargs["organization_id"]},
        )


@login_required
def accept_invitation_view(request, invitation_token):
    """View to handle invitation acceptance"""

    # Get the current user
    user = request.user

    # Verify all requirements for accepting the invitation
    is_verified, message, invitation = verify_invitation_for_acceptance(
        user, invitation_token
    )
    if not is_verified:
        messages.error(request, message)
        return redirect("home")

    # Accept the invitation
    accept_invitation(user, invitation)

    messages.success(
        request, f"Welcome to {invitation.organization.title}, {user.username}"
    )

    # Note: redirect user to org dashboard when the page is built
    return redirect("home")
