# from django.contrib.auth.mixins import LoginRequiredMixin
# from .mixins import (
#     WorkspaceTeamRequiredMixin,
#     WorkspaceTeamContextMixin,
# )
# from .base_views import BaseEntryListView
# from ..constants import EntryType
# from ..selectors import get_entries
# from django.db.models import QuerySet
# from typing import Any
# from .base_views import BaseEntryCreateView, BaseEntryUpdateView, BaseEntryDeleteView
# from django.urls import reverse
# from ..forms import CreateWorkspaceTeamEntryForm, UpdateWorkspaceTeamEntryForm
# from django.contrib import messages
# from django.http import HttpResponse
# from django.template.loader import render_to_string
# from ..constants import CONTEXT_OBJECT_NAME


# class WorkspaceTeamEntryListView(
#     LoginRequiredMixin,
#     WorkspaceTeamRequiredMixin,
#     WorkspaceTeamContextMixin,
#     BaseEntryListView,
# ):
#     template_name = "entries/team_level_entry.html"

#     def get_entry_type(self):
#         return EntryType.INCOME

#     def get_delete_url(self) -> str:
#         return reverse(
#             "workspace_team_entry_delete",
#             kwargs={
#                 "organization_id": self.organization.pk,
#                 "workspace_id": self.workspace.pk,
#                 "workspace_team_id": self.workspace_team.pk,
#                 "pk": self.entry.pk,
#             },
#         )

#     def get_queryset(self) -> QuerySet[Any]:
#         return get_entries(
#             organization=self.organization,
#             workspace_team=self.workspace_team,
#             entry_types=[
#                 EntryType.INCOME,
#                 EntryType.DISBURSEMENT,
#                 EntryType.REMITTANCE,
#             ],
#         )


# class WorkspaceTeamEntryCreateView(
#     LoginRequiredMixin,
#     WorkspaceTeamRequiredMixin,
#     WorkspaceTeamContextMixin,
#     BaseEntryCreateView,
# ):
#     # Override the form class of CreateEntryFormMixin
#     form_class = CreateWorkspaceTeamEntryForm

#     def get_entry_type(self):
#         return EntryType.INCOME

#     def get_queryset(self) -> QuerySet[Any]:
#         return get_entries(
#             organization=self.organization,
#             workspace_team=self.workspace_team,
#             entry_types=[
#                 EntryType.INCOME,
#                 EntryType.DISBURSEMENT,
#                 EntryType.REMITTANCE,
#             ],
#         )

#     def get_modal_title(self) -> str:
#         return ""

#     def get_post_url(self) -> str:
#         return reverse(
#             "workspace_team_entry_create",
#             kwargs={
#                 "organization_id": self.organization.pk,
#                 "workspace_id": self.workspace.pk,
#                 "workspace_team_id": self.workspace_team.pk,
#             },
#         )

#     def form_valid(self, form):
#         from ..services import create_entry_with_attachments

#         create_entry_with_attachments(
#             submitter=self.workspace_team_member,
#             amount=form.cleaned_data["amount"],
#             description=form.cleaned_data["description"],
#             attachments=form.cleaned_data["attachment_files"],
#             entry_type=form.cleaned_data["entry_type"],
#             workspace=self.workspace,
#             workspace_team=self.workspace_team,
#         )

#         messages.success(self.request, "Entry created successfully")
#         return self._render_htmx_success_response()

#     def _render_htmx_success_response(self) -> HttpResponse:
#         base_context = self.get_context_data()

#         from apps.core.utils import get_paginated_context

#         workspace_team_entries = self.get_queryset()
#         table_context = get_paginated_context(
#             queryset=workspace_team_entries,
#             context=base_context,
#             object_name=CONTEXT_OBJECT_NAME,
#         )

#         table_html = render_to_string(
#             "entries/partials/table.html", context=table_context, request=self.request
#         )
#         message_html = render_to_string(
#             "includes/message.html", context=base_context, request=self.request
#         )

#         response = HttpResponse(f"{message_html}{table_html}")
#         response["HX-trigger"] = "success"
#         return response


# class WorkspaceTeamEntryUpdateView(
#     LoginRequiredMixin,
#     WorkspaceTeamRequiredMixin,
#     WorkspaceTeamContextMixin,
#     BaseEntryUpdateView,
# ):
#     form_class = UpdateWorkspaceTeamEntryForm

#     def get_entry_type(self):
#         return EntryType.INCOME

#     def get_queryset(self):
#         return get_entries(
#             organization=self.organization,
#             workspace_team=self.workspace_team,
#             entry_types=[
#                 EntryType.INCOME,
#                 EntryType.DISBURSEMENT,
#                 EntryType.REMITTANCE,
#             ],
#         )

#     def get_modal_title(self) -> str:
#         return "Workspace Team Entry"

#     def get_post_url(self) -> str:
#         return reverse(
#             "workspace_team_entry_update",
#             kwargs={
#                 "organization_id": self.organization.pk,
#                 "workspace_id": self.workspace.pk,
#                 "workspace_team_id": self.workspace_team.pk,
#                 "pk": self.entry.pk,
#             },
#         )


# class WorkspaceTeamEntryDeleteView(
#     LoginRequiredMixin,
#     WorkspaceTeamRequiredMixin,
#     WorkspaceTeamContextMixin,
#     BaseEntryDeleteView,
# ):
#     def get_queryset(self):
#         return get_entries(
#             organization=self.organization,
#             workspace_team=self.workspace_team,
#             entry_types=[
#                 EntryType.INCOME,
#                 EntryType.DISBURSEMENT,
#                 EntryType.REMITTANCE,
#             ],
#         )
