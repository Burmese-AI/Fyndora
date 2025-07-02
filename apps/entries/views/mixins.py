from typing import Any

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages

from apps.workspaces.models import Workspace
from apps.organizations.selectors import get_user_org_membership
from apps.organizations.models import Organization

from ..models import Entry


class OrganizationRequiredMixin:
    organization = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        organization_id = kwargs.get("organization_id")
        self.organization = get_object_or_404(Organization, pk=organization_id)


class OrganizationMemberRequiredMixin(OrganizationRequiredMixin):
    org_member = None

    def setup(self, request, *args, **kwargs):
        # Ensures organization is set
        super().setup(request, *args, **kwargs)
        self.org_member = get_user_org_membership(self.request.user, self.organization)


class WorkspaceRequiredMixin(OrganizationRequiredMixin):
    workspace = None
    
    def setup(self, request, *args, **kwargs):
        # Ensures organization is set
        super().setup(request, *args, **kwargs)
        workspace_id = kwargs.get("workspace_id")
        self.workspace = get_object_or_404(Workspace, pk=workspace_id)


class EntryRequiredMixin():
    entry = None
    attachments = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        entry_id = kwargs.get("pk")
        self.entry = get_object_or_404(Entry, pk=entry_id)
        self.attachments = self.entry.attachments.all()


class HtmxOobResponseMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            context["is_oob"] = True
        return context


class HtmxModalFormInvalidFormResponseMixin:
    message_template_name = "includes/message.html"
    modal_template_name = None
    
    def form_invalid(self, form):
        messages.error(self.request, "Form submission failed")
        return self.render_htmx_error_response(form)
    
    def render_htmx_error_response(self, form) -> HttpResponse:
        base_context = self.get_context_data()
        modal_context = {
            **base_context,
            "form": form,
        }

        message_html = render_to_string(
            self.message_template_name,
            context=base_context,
            request=self.request
        )
        modal_html = render_to_string(
            self.modal_template_name,
            context=modal_context,
            request=self.request
        )

        return HttpResponse(f"{message_html}{modal_html}")


class OrganizationContextMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization if hasattr(self, "organization") else None
        context["org_member"] = self.org_member if hasattr(self, "org_member") else None
        context["entry"] = self.entry if hasattr(self, "entry") else None
        context["attachments"] = self.attachments if hasattr(self, "attachments") else None
        return context
    

class WorkspaceContextMixin(OrganizationContextMixin):
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["workspace"] = self.workspace if hasattr(self, "workspace") else None
        return context
