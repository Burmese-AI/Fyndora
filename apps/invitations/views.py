from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.db import transaction
from .models import Invitation
from .forms import InvitationCreateForm
from apps.organizations.models import Organization, OrganizationMember

class InvitationListView(LoginRequiredMixin, ListView):
    model = Invitation
    template_name = 'invitations/index.html'
    context_object_name = 'invitations'

    def get_queryset(self):
        return Invitation.objects.all()

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
        print("\n>>> Starting form_valid")
        invitation = form.save(commit=False)
        print(f">>> Before save - PK: {invitation.pk}")
        
        # Explicitly set fields
        invitation.organization = self.organization
        invitation.invited_by = OrganizationMember.objects.get(
            user=self.request.user,
            organization=self.organization
        )
        
        print(f">>> Before final save - PK: {invitation.pk}")
        invitation.save()
        print(f">>> After save - PK: {invitation.pk}")
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('invitation_list', kwargs={'organization_id': self.kwargs['organization_id']})