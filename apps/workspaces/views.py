from apps.workspaces.models import Workspace
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.workspaces.selectors import get_user_workspaces
from apps.workspaces.forms import WorkspaceForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect
from apps.workspaces.services import create_workspace_with_admin
from apps.workspaces.exceptions import WorkspaceCreationError
from apps.organizations.models import Organization


# Create your views here.
class WorkspaceListView(ListView, LoginRequiredMixin):
    model = Workspace
    template_name = "workspaces/workspaces_list.html"
    context_object_name = "workspaces"

    def get_queryset(self):
        return get_user_workspaces(self.request.user)


@login_required
def create_workspace(request):
    try:
        if request.method == "POST":
            form = WorkspaceForm(request.POST)
            if form.is_valid():
                try:
                    # Get the organization from the request
                    organization = Organization.objects.get(
                        organization_id=request.POST.get('organization_id')
                    )
                    
                    create_workspace_with_admin(
                        form=form,
                        user=request.user,
                        organization=organization
                    )

                    if request.headers.get("HX-Request"):
                        messages.success(request, "Workspace created successfully!")
                        return HttpResponseClientRedirect("/")
                except WorkspaceCreationError as e:
                    messages.error(request, str(e))
                    if request.headers.get("HX-Request"):
                        return HttpResponseClientRedirect("/")
                    return render(
                        request, "workspaces/workspace_form.html", {"form": form}
                    )
        else:
            form = WorkspaceForm()
        return render(request, "workspaces/workspace_form.html", {"form": form})
    except Exception:
        if request.headers.get("HX-Request"):
            messages.error(
                request, "An unexpected error occurred. Please try again later."
            )
            return HttpResponseClientRedirect("/")
        raise WorkspaceCreationError(
            "An unexpected error occurred. Please try again later."
        )