from django.shortcuts import render
from apps.workspaces.models import Workspace
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

# Create your views here.
class WorkspaceListView(ListView, LoginRequiredMixin):
    model = Workspace
    template_name = "workspaces\workspaces_list.html"
    context_object_name = "workspaces"

    def get_queryset(self):
        try:
            # Get all organization memberships of the current user
            user_org_memberships = self.request.user.organization_memberships.all()
            print(user_org_memberships)
            
            # Get workspaces where user is a member of the organization
            return Workspace.objects.filter(
                organization_id__in=user_org_memberships.values_list('organization_id', flat=True)
            )
        except Exception as e:
            print(f"Error fetching workspaces: {str(e)}")
            return Workspace.objects.none()
