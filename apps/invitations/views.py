from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from .models import Invitation
from .forms import InvitationCreateForm
from apps.organizations.models import Organization, OrganizationMember

class InvitationListView(LoginRequiredMixin, ListView):
    model = Invitation
    template_name = 'invitations/index.html'
    context_object_name = 'invitations'

    def get_queryset(self):
        return Invitation.objects.filter(organization=self.kwargs['organization_id'])

class InvitationCreateView(LoginRequiredMixin, CreateView):
    model = Invitation
    form_class = InvitationCreateForm
    template_name = 'invitations/create.html'

    def __init__(self):
        self.organization = None

    def dispatch(self, request, *args, **kwargs):
        #Get ORG ID from URL
        organization_id = self.kwargs['organization_id']
        self.organization = get_object_or_404(Organization, pk=organization_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass additional data to the kwargs which Form class will receive when initializing
        kwargs['organization'] = self.organization
        kwargs['user'] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        invitation = form.save(commit=False)
        # Set the organization and invited_by fields before saving the form
        invitation.organization = self.organization
        invitation.invited_by = OrganizationMember.objects.get(user=self.request.user, organization=self.organization)
        invitation.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('invitation_list', kwargs={'organization_id': self.kwargs['organization_id']})
    
@login_required
@transaction.atomic
def accept_invitation(request, invitation_token):
    # Get the current user
    user = request.user
    # Verify the invitation token
    is_verified, message, invitation = verify_invitation(user, invitation_token)
    
    # If not legit, redirect back to the home page with an error msg
    if not is_verified:
        messages.error(request, message)
    else:    
        # If legit, add user to org
        OrganizationMember.objects.create(
            user=user,
            organization=invitation.organization
        )
        invitation.is_used = True
        invitation.is_active = False
        invitation.save()
        messages.success(request, f"Welcome to {invitation.organization.title}, {user.username}")
        
        #Note: redirect user to org dashboard when the page is built
    return redirect('home')
    
def verify_invitation(user, invitation_token: str) -> tuple:
    try:
        # Get the invitation withe the given token
        invitation = Invitation.objects.get(token=invitation_token)
    except Invitation.DoesNotExist:
        return False, "Invalid Invitation Link", None
    
    # Check if the invitation is for this user
    if invitation.email != user.email:
        return False, "Invitation link is not for this user account", None
    
    # Check if the user has already joined the org
    user_exists_in_org = OrganizationMember.objects.filter(user=user, organization=invitation.organization).exists()
    if user_exists_in_org:
        return False, "You have already joined this organization", None
          
    # Check if it's still valid
    if not invitation.is_valid:
        return False, "Invitation link is expired", None
    
    return True, "Invitation verified successfully", invitation
    
    