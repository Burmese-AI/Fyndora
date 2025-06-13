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

class InvitationListView(LoginRequiredMixin, ListView):
    model = Invitation
    template_name = "invitations/index.html"
    context_object_name = "invitations"
    paginate_by = PAGINATION_SIZE

    def get_queryset(self):
        organization = get_object_or_404(Organization, pk=self.kwargs["organization_id"])
        return Invitation.objects.filter(organization=organization)
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "invitations"
        return context
    
    def render_to_response(self, context: dict[str, Any], **response_kwargs: Any):
        if self.request.htmx:
            return render(self.request, "invitations/partials/table.html", context)
        return super().render_to_response(context, **response_kwargs)

class InvitationCreateView(LoginRequiredMixin, CreateView):
    model = Invitation
    form_class = InvitationCreateForm
    template_name = "invitations/create.html"

    def __init__(self):
        self.organization = None

    def dispatch(self, request, *args, **kwargs):
        # Get ORG ID from URL
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass additional data to the kwargs which Form class will receive when initializing
        kwargs["organization"] = self.organization
        kwargs["user"] = self.request.user
        return kwargs

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
        return super().form_valid(form)

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

@login_required
def open_invitation_create_modal(request):
    return render(request, "invitations/components/create_modal.html")