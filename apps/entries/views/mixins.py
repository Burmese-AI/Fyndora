from typing import Any

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages

from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.teams.models import TeamMember
from apps.organizations.models import Organization, OrganizationMember

from ..forms import BaseEntryForm, UpdateEntryForm
from ..models import Entry


class OrganizationRequiredMixin:
    """ """

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


class WorkspaceRequiredMixin(OrganizationRequiredMixin):
    """ """

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
        self.workspace_team_member = get_object_or_404(
            TeamMember,
            team=self.workspace_team.team,
            organization_member=self.org_member,
        )
        self.workspace_team_role = self.workspace_team_member.role


class EntryRequiredMixin:
    entry = None
    attachments = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        entry_id = kwargs.get("pk")
        self.entry = get_object_or_404(Entry, pk=entry_id)
        self.attachments = self.entry.attachments.all()


class EntryFormMixin:
    form_class = BaseEntryForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["org_member"] = self.org_member
        kwargs["organization"] = self.organization
        kwargs["is_org_admin"] = self.is_org_admin
        kwargs["is_workspace_admin"] = (
            self.is_workspace_admin if hasattr(self, "is_workspace_admin") else None
        )
        kwargs["is_operation_reviewer"] = (
            self.is_operation_reviewer
            if hasattr(self, "is_operation_reviewer")
            else None
        )
        kwargs["is_team_coordinator"] = (
            self.is_team_coordinator if hasattr(self, "is_team_coordinator") else None
        )
        kwargs["workspace"] = self.workspace if hasattr(self, "workspace") else None
        kwargs["workspace_team"] = (
            self.workspace_team if hasattr(self, "workspace_team") else None
        )
        kwargs["workspace_team_role"] = (
            self.workspace_team_role if hasattr(self, "workspace_team_role") else None
        )
        kwargs["workspace_team_member"] = (
            self.workspace_team_member
            if hasattr(self, "workspace_team_member")
            else None
        )
        return kwargs


class CreateEntryFormMixin(EntryFormMixin):
    form_class = BaseEntryForm


class UpdateEntryFormMixin(EntryFormMixin):
    form_class = UpdateEntryForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = getattr(self, "entry", None)
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


class OrganizationContextMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["organization"] = (
            self.organization if hasattr(self, "organization") else None
        )
        context["org_member"] = self.org_member if hasattr(self, "org_member") else None
        context["entry"] = self.entry if hasattr(self, "entry") else None
        context["attachments"] = (
            self.attachments if hasattr(self, "attachments") else None
        )
        return context


class WorkspaceContextMixin(OrganizationContextMixin):
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["workspace"] = self.workspace if hasattr(self, "workspace") else None
        return context


class WorkspaceTeamContextMixin(WorkspaceContextMixin):
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["workspace_team"] = (
            self.workspace_team if hasattr(self, "workspace_team") else None
        )
        context["workspace_team_member"] = (
            self.workspace_team_member
            if hasattr(self, "workspace_team_member")
            else None
        )
        return context


class EntryUrlIdentifierMixin:
    def get_entry_type(self):
        raise NotImplementedError("You must implement get_entry_type() in the subclass")

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["entry_type"] = self.get_entry_type()
        return context
