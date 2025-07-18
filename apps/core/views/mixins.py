from typing import Any
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from apps.organizations.models import Organization, OrganizationMember
from django.template.loader import render_to_string

class OrganizationRequiredMixin:
    """
        Mixin for organization required.
    """

    organization = None
    org_member = None
    is_org_admin = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        organization_id = kwargs.get("organization_id")
        self.organization = get_object_or_404(Organization, pk=organization_id)
        self.org_member = get_object_or_404(
            OrganizationMember, user=self.request.user, organization=self.organization
        )
        self.is_org_admin = self.org_member == self.organization.owner
        
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
        return self._render_htmx_error_response(form)

    def _render_htmx_error_response(self, form) -> HttpResponse:
        base_context = self.get_context_data()
        modal_context = {
            **base_context,
            "form": form,
        }

        message_html = render_to_string(
            self.message_template_name, context=base_context, request=self.request
        )
        modal_html = render_to_string(
            self.modal_template_name, context=modal_context, request=self.request
        )

        return HttpResponse(f"{message_html}{modal_html}")
