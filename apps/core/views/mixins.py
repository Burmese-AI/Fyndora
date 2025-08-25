from typing import Any
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from apps.organizations.models import Organization, OrganizationMember
from django.template.loader import render_to_string
from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.core.permissions import WorkspacePermissions
from apps.workspaces.selectors import (
    get_workspace_team_member_by_workspace_team_and_org_member,
)


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
            OrganizationMember, user=request.user, organization=self.organization
        )
        self.is_org_admin = self.org_member == self.organization.owner

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["org_member"] = self.org_member
        context["is_org_admin"] = self.is_org_admin
        return context


class WorkspaceRequiredMixin(OrganizationRequiredMixin):
    """
    Mixin for workspace required.
    """

    workspace = None
    is_workspace_admin = None
    is_operation_reviewer = None

    

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        workspace_id = kwargs.get("workspace_id")
        self.workspace = get_object_or_404(
            Workspace, pk=workspace_id, organization=self.organization
        )
        self.is_workspace_admin = self.workspace.workspace_admin == self.org_member
        self.is_operation_reviewer = (
            self.workspace.operations_reviewer == self.org_member
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["workspace"] = self.workspace
        context["is_workspace_admin"] = self.is_workspace_admin
        context["is_operation_reviewer"] = self.is_operation_reviewer
        context["permissions"] = {
            "can_add_workspace_exchange_rate": self.request.user.has_perm(
                WorkspacePermissions.ADD_WORKSPACE_CURRENCY, self.workspace
            ),
            "can_change_workspace_exchange_rate": self.request.user.has_perm(
                WorkspacePermissions.CHANGE_WORKSPACE_CURRENCY, self.workspace
            ),
            "can_delete_workspace_exchange_rate": self.request.user.has_perm(
                WorkspacePermissions.DELETE_WORKSPACE_CURRENCY, self.workspace
            ),
        }
        return context


class WorkspaceTeamRequiredMixin(WorkspaceRequiredMixin):
    workspace_team = None
    workspace_team_member = None
    workspace_team_role = None
    is_team_coordinator = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        workspace_team_id = kwargs.get("workspace_team_id")
        self.workspace_team = get_object_or_404(
            WorkspaceTeam, pk=workspace_team_id, workspace=self.workspace
        )
        self.workspace_team_member = (
            get_workspace_team_member_by_workspace_team_and_org_member(
                workspace_team=self.workspace_team, org_member=self.org_member
            )
        )
        self.workspace_team_role = (
            self.workspace_team_member.role if self.workspace_team_member else None
        )
        self.is_team_coordinator = (
            self.org_member == self.workspace_team.team.team_coordinator
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["workspace_team"] = self.workspace_team
        context["workspace_team_member"] = self.workspace_team_member
        context["workspace_team_role"] = self.workspace_team_role
        context["is_team_coordinator"] = self.is_team_coordinator
        return context


class UpdateFormMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = getattr(self, "instance", None)
        return kwargs


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


class HtmxInvalidResponseMixin:
    """
    Mixin for htmx invalid response.
    """

    message_template_name = "includes/message.html"

    def _render_htmx_error_response(self, form=None) -> HttpResponse:
        """
        Render htmx error response.
        Note: Form is not required
        """
        base_context = self.get_context_data()

        message_html = render_to_string(
            self.message_template_name, context=base_context, request=self.request
        )

        return HttpResponse(f"{message_html}")
