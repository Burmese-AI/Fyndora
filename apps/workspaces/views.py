from typing import Any

from django.urls import reverse_lazy
from apps.core.views.base_views import BaseGetModalFormView
from apps.core.views.crud_base_views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)
from apps.workspaces.forms import WorkspaceExchangeRateUpdateForm, WorkspaceForm
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django_htmx.http import HttpResponseClientRedirect
from apps.workspaces.selectors import (
    get_organization_by_id,
)
from apps.workspaces.services import create_workspace_from_form
from django.contrib import messages
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.workspaces.selectors import (
    get_workspace_by_id,
    get_team_by_id,
)
from apps.organizations.selectors import get_orgMember_by_user_id_and_organization_id
from apps.workspaces.services import update_workspace_from_form
from django.template.loader import render_to_string
from django.http import HttpResponse
from apps.workspaces.forms import (
    AddTeamToWorkspaceForm,
    WorkspaceExchangeRateCreateForm,
)
from apps.workspaces.exceptions import AddTeamToWorkspaceError
from apps.workspaces.selectors import get_workspace_teams_by_workspace_id
from apps.workspaces.selectors import get_workspaces_with_team_counts
from apps.workspaces.services import remove_team_from_workspace, add_team_to_workspace
from django.contrib.auth.models import Group
from apps.workspaces.forms import ChangeWorkspaceTeamRemittanceRateForm
from apps.workspaces.selectors import (
    get_workspace_team_by_workspace_team_id,
    get_all_related_workspace_teams,
    get_workspace_exchange_rates,
)
from apps.workspaces.services import update_workspace_team_remittance_rate_from_form
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from apps.workspaces.selectors import get_single_workspace_with_team_counts
from apps.core.utils import permission_denied_view
from apps.core.permissions import WorkspacePermissions
from apps.core.permissions import OrganizationPermissions
from apps.workspaces.permissions import (
    check_create_workspace_permission,
    check_change_workspace_admin_permission,
    check_change_workspace_permission,
)
from .models import WorkspaceExchangeRate
from apps.currencies.constants import (
    EXCHANGE_RATE_CONTEXT_OBJECT_NAME,
    EXCHANGE_RATE_DETAIL_CONTEXT_OBJECT_NAME,
)
from apps.currencies.views.mixins import ExchangeRateUrlIdentifierMixin
from apps.core.views.mixins import WorkspaceRequiredMixin
from apps.core.utils import get_paginated_context
from .mixins.workspace_exchange_rate.required_mixins import (
    WorkspaceExchangeRateRequiredMixin,
)
from apps.core.utils import can_manage_organization
from apps.remittance.services import (
    process_due_amount,
    update_remittance_based_on_entry_status_change,
)
from apps.workspaces.permissions import (
    assign_workspace_team_permissions,
    remove_workspace_team_permissions,
)
from apps.workspaces.selectors import get_workspace_team_by_workspace_id_and_team_id


@login_required
def get_workspaces_view(request, organization_id):
    try:
        organization = get_organization_by_id(organization_id)
        if not can_manage_organization(request.user, organization):
            return permission_denied_view(
                request,
                "You do not have permission to access this organization.",
            )
        workspaces = get_workspaces_with_team_counts(organization_id)
        return render(
            request,
            "workspaces/index.html",
            {
                "workspaces": workspaces,
                "organization": organization,
            },
        )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def create_workspace_view(request, organization_id):
    try:
        organization = get_organization_by_id(organization_id)
        orgMember = get_orgMember_by_user_id_and_organization_id(
            request.user.user_id, organization_id
        )
        # check if the user has the permission to add a workspace to the organization (only org owner and workspace admin can add a workspace to the organization)
        permission_check = check_create_workspace_permission(request, organization)
        if permission_check:
            return permission_check

        if request.method == "POST":
            form = WorkspaceForm(request.POST, organization=organization)
            try:
                if form.is_valid():
                    create_workspace_from_form(
                        form=form, orgMember=orgMember, organization=organization
                    )
                    messages.success(request, "Workspace created successfully.")
                    if request.headers.get("HX-Request"):
                        organization = get_organization_by_id(organization_id)
                        workspaces = get_workspaces_with_team_counts(organization_id)
                        context = {
                            "workspaces": workspaces,
                            "organization": organization,
                            "is_oob": True,
                        }
                        message_html = render_to_string(
                            "includes/message.html", context=context, request=request
                        )
                        workspaces_grid_html = render_to_string(
                            "workspaces/partials/workspaces_grid.html",
                            context=context,
                            request=request,
                        )
                        response = HttpResponse(
                            f"{message_html} {workspaces_grid_html}"
                        )
                        response["HX-trigger"] = "success"
                        return response
                else:
                    messages.error(request, "Invalid form data.")
                    context = {"form": form, "is_oob": True}
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    modal_html = render_to_string(
                        "workspaces/partials/create_workspace_form.html",
                        context=context,
                        request=request,
                    )
                    return HttpResponse(f"{message_html} {modal_html}")
            except WorkspaceCreationError as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
        else:
            form = WorkspaceForm(request.POST or None, organization=organization)
        context = {
            "form": form,
            "organization": organization,
        }
        return render(
            request,
            "workspaces/partials/create_workspace_form.html",
            context,
        )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def edit_workspace_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        previous_workspace_admin = workspace.workspace_admin
        previous_operations_reviewer = workspace.operations_reviewer

        permission_check = check_change_workspace_permission(request, workspace)
        if permission_check:
            return permission_check  # this will route to the permission denied view

        if request.method == "POST":
            if request.POST.get("workspace_admin") is not None:
                if previous_workspace_admin != request.POST.get("workspace_admin"):
                    permission_check = check_change_workspace_admin_permission(
                        request, organization
                    )
                if permission_check:
                    return permission_check  # this will route to the permission denied view

            form_data = request.POST.copy()
            if "workspace_admin" not in form_data:
                form_data["workspace_admin"] = previous_workspace_admin

            form = WorkspaceForm(
                form_data, instance=workspace, organization=organization
            )
            try:
                print(f"Workspace before updating => {workspace.remittance_rate}")
                old_remittance_rate = workspace.remittance_rate
                if form.is_valid():
                    update_workspace_from_form(
                        form=form,
                        workspace=workspace,
                        previous_workspace_admin=previous_workspace_admin,
                        previous_operations_reviewer=previous_operations_reviewer,
                    )
                    print(form.cleaned_data["remittance_rate"])

                    # If remittance rate is changed, update all due amounts of workspace teams' remitances
                    if old_remittance_rate != form.cleaned_data["remittance_rate"]:
                        print("Remittance Rate Changed")
                        # Get All Workspace Teams
                        workspace_teams = workspace.workspace_teams.all()
                        print(f"Workspace Teams: {workspace_teams}")
                        # Update Remittance Due Amount of Each Team's Remittance
                        for workspace_team in workspace_teams:
                            remittance = workspace_team.remittance
                            new_due_amount = process_due_amount(
                                workspace_team, remittance
                            )
                            print(f"New Due Amount: {new_due_amount}")
                            update_remittance_based_on_entry_status_change(
                                remittance=remittance, due_amount=new_due_amount
                            )

                    workspace = get_single_workspace_with_team_counts(workspace_id)
                    context = {
                        "workspace": workspace,
                        "organization": organization,
                        "is_oob": True,
                    }

                    messages.success(request, "Workspace updated successfully.")
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    workspace_card_html = render_to_string(
                        "workspaces/partials/workspace_card.html",
                        context=context,
                        request=request,
                    )
                    response = HttpResponse(f"{message_html} {workspace_card_html}")
                    response["HX-trigger"] = "success"
                    return response
                else:
                    messages.error(request, "Invalid form data.")
                    context = {
                        "form": form,
                        "is_oob": True,
                        "organization": organization,
                    }
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    modal_html = render_to_string(
                        "workspaces/partials/edit_workspace_form.html",
                        context=context,
                        request=request,
                    )
                    return HttpResponse(f"{message_html} {modal_html}")
            except WorkspaceUpdateError as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
        else:
            form = WorkspaceForm(
                instance=workspace,
                organization=organization,
                can_change_workspace_admin=request.user.has_perm(
                    OrganizationPermissions.CHANGE_WORKSPACE_ADMIN, organization
                ),
            )

        context = {
            "form": form,
            "organization": organization,
        }
        return render(request, "workspaces/partials/edit_workspace_form.html", context)
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def delete_workspace_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)

        if not request.user.has_perm(WorkspacePermissions.DELETE_WORKSPACE, workspace):
            return permission_denied_view(
                request,
                "You do not have permission to delete this workspace.",
            )

        if request.method == "POST":
            group_name = f"Workspace Admins - {workspace_id}"
            group = Group.objects.filter(name=group_name).first()
            group.delete()
            workspace.delete()
            messages.success(request, "Workspace deleted successfully.")
            organization = get_organization_by_id(organization_id)
            workspaces = get_workspaces_with_team_counts(organization_id)
            context = {
                "workspaces": workspaces,
                "organization": organization,
                "is_oob": True,
            }
            message_html = render_to_string(
                "includes/message.html", context=context, request=request
            )
            workspaces_grid_html = render_to_string(
                "workspaces/partials/workspaces_grid.html",
                context=context,
                request=request,
            )

            response = HttpResponse(f"{message_html} {workspaces_grid_html}")
            response["HX-trigger"] = "success"
            return response

        else:
            context = {
                "workspace": workspace,
                "organization": organization,
            }
        return render(
            request, "workspaces/partials/delete_workspace_form.html", context
        )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def add_team_to_workspace_view(request, organization_id, workspace_id):
    try:
        organization = get_organization_by_id(organization_id)
        workspace = get_workspace_by_id(workspace_id)

        if not request.user.has_perm(WorkspacePermissions.ASSIGN_TEAMS, workspace):
            return permission_denied_view(
                request,
                "You do not have permission to add teams to this workspace.",
            )

        if request.method == "POST":
            form = AddTeamToWorkspaceForm(
                request.POST, organization=organization, workspace=workspace
            )
            try:
                if form.is_valid():
                    workspace_team = add_team_to_workspace(
                        workspace_id,
                        form.cleaned_data["team"].team_id,
                        form.cleaned_data["custom_remittance_rate"],
                        workspace,
                    )
                    workspace = get_single_workspace_with_team_counts(workspace_id)
                    context = {
                        "workspace": workspace,
                        "organization": organization,
                        "is_oob": True,
                    }
                    workspace_team = get_workspace_team_by_workspace_team_id(
                        workspace_team.workspace_team_id
                    )
                    assign_workspace_team_permissions(
                        workspace_team, request_user=request.user
                    )
                    messages.success(request, "Team added to workspace successfully.")
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    workspace_card_html = render_to_string(
                        "workspaces/partials/workspace_card.html",
                        context=context,
                        request=request,
                    )
                    response = HttpResponse(f"{workspace_card_html} {message_html} ")
                    response["HX-trigger"] = "success"
                    return response
                else:
                    messages.error(request, "Invalid form data.")
                    context = {
                        "form": form,
                        "is_oob": True,
                    }
                    message_html = render_to_string(
                        "includes/message.html", context=context, request=request
                    )
                    add_team_form_html = render_to_string(
                        "workspaces/partials/add_workspace_team_form.html",
                        context=context,
                        request=request,
                    )
                    response = HttpResponse(f"{add_team_form_html} {message_html}")
                    return response
            except AddTeamToWorkspaceError as e:
                messages.error(request, str(e))
                return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")
        else:
            form = AddTeamToWorkspaceForm(organization=organization)
            context = {
                "form": form,
                "organization": organization,
                "workspace": workspace,
            }
            return render(
                request, "workspaces/partials/add_workspace_team_form.html", context
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(f"/{organization_id}/workspaces/")


@login_required
def get_workspace_teams_view(request, organization_id, workspace_id):
    try:
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        workspace_teams = get_workspace_teams_by_workspace_id(workspace_id)

        context = {
            "workspace_teams": workspace_teams,
            "workspace": workspace,
            "organization": organization,
            "view": "teams",
            "hide_management_access": False,
        }
        return render(request, "workspace_teams/index.html", context)
    except Exception as e:
        print(f"DEBUG: An unexpected error occurred: {str(e)}")
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return render(request, "workspace_teams/index.html", context)


@login_required
def remove_team_from_workspace_view(request, organization_id, workspace_id, team_id):
    try:
        team = get_team_by_id(team_id)
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        workspace_team = get_workspace_team_by_workspace_id_and_team_id(
            workspace_id, team_id
        )
        if request.method == "POST":
            # unnecessary to remove permissions as the workspace team will be deleted
            # remove_workspace_team_permissions(workspace_team, request_user=request.user)
            remove_team_from_workspace(workspace_team)
            messages.success(request, "Team removed from workspace successfully.")
            workspace_teams = get_workspace_teams_by_workspace_id(workspace_id)
            context = {
                "workspace_teams": workspace_teams,
                "workspace": workspace,
                "organization": organization,
                "is_oob": True,
            }
            workspace_team_grid_html = render_to_string(
                "workspace_teams/partials/workspace_teams_grid.html",
                context=context,
                request=request,
            )
            message_html = render_to_string(
                "includes/message.html", context=context, request=request
            )
            response = HttpResponse(f"{message_html} {workspace_team_grid_html}")
            response["HX-trigger"] = "success"
            return response
        else:
            return render(
                request,
                "workspace_teams/partials/remove_workspace_team_form.html",
                {"team": team, "workspace": workspace, "organization": organization},
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect(
            "get_workspace_teams",
            organization_id=organization_id,
            workspace_id=workspace_id,
        )


@login_required
def change_workspace_team_remittance_rate_view(
    request, organization_id, workspace_id, team_id, workspace_team_id
):
    try:
        workspace_team = get_workspace_team_by_workspace_team_id(workspace_team_id)
        workspace = get_workspace_by_id(workspace_id)
        organization = get_organization_by_id(organization_id)
        team = get_team_by_id(team_id)
        if request.method == "POST":
            form = ChangeWorkspaceTeamRemittanceRateForm(
                request.POST, instance=workspace_team, workspace=workspace
            )
            if form.is_valid():
                # Updating Team Lvl Remittance Rate
                update_workspace_team_remittance_rate_from_form(
                    form=form, workspace_team=workspace_team, workspace=workspace
                )
                # Updating due amount of remittance
                remittance = workspace_team.remittance
                new_due_amount = process_due_amount(workspace_team, remittance)
                update_remittance_based_on_entry_status_change(
                    remittance=remittance,
                    due_amount=new_due_amount,
                )
                messages.success(request, "Remittance rate updated successfully.")
                workspace_team = get_workspace_team_by_workspace_team_id(
                    workspace_team_id
                )
                context = {
                    "workspace_team": workspace_team,
                    "workspace": workspace,
                    "organization": organization,
                    "is_oob": True,
                }
                workspace_team_card_html = render_to_string(
                    "workspace_teams/partials/workspace_team_card.html",
                    context=context,
                    request=request,
                )
                message_html = render_to_string(
                    "includes/message.html",
                    context=context,
                    request=request,
                )
                response = HttpResponse(f"{message_html} {workspace_team_card_html}")
                response["HX-trigger"] = "success"
                return response
            else:
                messages.error(request, "Invalid form data.")
                context = {
                    "form": form,
                    "workspace_team": workspace_team,
                    "organization": organization,
                    "team": team,
                    "workspace": workspace,
                    "is_oob": True,
                }
                modal_html = render_to_string(
                    "workspace_teams/partials/edit_workspace_team_remittance_form.html",
                    context=context,
                    request=request,
                )
                message_html = render_to_string(
                    "includes/message.html",
                    context=context,
                    request=request,
                )
                response = HttpResponse(f"{message_html} {modal_html}")
                return response
        else:
            form = ChangeWorkspaceTeamRemittanceRateForm(instance=workspace_team)
            context = {
                "form": form,
                "organization": organization,
                "workspace_team": workspace_team,
                "workspace": workspace,
                "team": team,
            }
            return render(
                request,
                "workspace_teams/partials/edit_workspace_team_remittance_form.html",
                context,
            )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return HttpResponseClientRedirect(
            f"/{organization_id}/workspaces/{workspace_id}/teams"
        )


class SubmissionTeamListView(LoginRequiredMixin, TemplateView):
    template_name = "workspace_teams/index_2.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = get_organization_by_id(self.kwargs["organization_id"])
        context["hide_management_access"] = True
        grouped_teams = get_all_related_workspace_teams(
            organization=context["organization"],
            user=self.request.user,
            group_by_workspace=True,
        )
        context["workspace_teams"] = dict(grouped_teams)
        return context


class WorkspaceExchangeRateListView(
    WorkspaceRequiredMixin,
    ExchangeRateUrlIdentifierMixin,
    BaseListView,
    LoginRequiredMixin,
):
    model = WorkspaceExchangeRate
    context_object_name = EXCHANGE_RATE_CONTEXT_OBJECT_NAME
    template_name = "workspace_exchange_rates/index.html"
    table_template_name = ""

    def get_queryset(self):
        return get_workspace_exchange_rates(
            organization=self.organization,
            workspace=self.workspace,
        )

    def get_exchange_rate_level(self):
        return "workspace"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "exchange_rates"
        return context


class WorkspaceExchangeRateCreateView(
    WorkspaceRequiredMixin,
    ExchangeRateUrlIdentifierMixin,
    BaseGetModalFormView,
    BaseCreateView,
    LoginRequiredMixin,
):
    model = WorkspaceExchangeRate
    form_class = WorkspaceExchangeRateCreateForm
    modal_template_name = "currencies/components/create_modal.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(
            WorkspacePermissions.ADD_WORKSPACE_CURRENCY, self.workspace
        ):
            return permission_denied_view(
                request,
                "You do not have permission to add exchange rates to this workspace.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_workspace_exchange_rates(
            organization=self.organization,
            workspace=self.workspace,
        )

    def get_post_url(self) -> str:
        return reverse_lazy(
            "workspace_exchange_rate_create",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
            },
        )

    def get_modal_title(self) -> str:
        return "Add Workpsace Exchange Rate"

    def get_exchange_rate_level(self):
        return "workspace"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["workspace"] = self.workspace
        return kwargs

    def form_valid(self, form):
        from .services import create_workspace_exchange_rate

        try:
            create_workspace_exchange_rate(
                workspace=self.workspace,
                organization_member=self.org_member,
                currency_code=form.cleaned_data["currency_code"],
                rate=form.cleaned_data["rate"],
                note=form.cleaned_data["note"],
                effective_date=form.cleaned_data["effective_date"],
            )
        except Exception as e:
            messages.error(self.request, f"{str(e)}")
            return self._render_htmx_error_response(form)
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        workspace_exchanage_rates = self.get_queryset()
        table_context = get_paginated_context(
            queryset=workspace_exchanage_rates,
            context=base_context,
            object_name="exchange_rates",
        )

        table_html = render_to_string(
            "currencies/partials/table.html",
            context=table_context,
            request=self.request,
        )
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )

        response = HttpResponse(f"{message_html}{table_html}")
        response["HX-trigger"] = "success"
        return response


class WorkspaceExchangeRateUpdateView(
    WorkspaceExchangeRateRequiredMixin,
    WorkspaceRequiredMixin,
    ExchangeRateUrlIdentifierMixin,
    BaseGetModalFormView,
    BaseUpdateView,
    LoginRequiredMixin,
):
    model = WorkspaceExchangeRate
    form_class = WorkspaceExchangeRateUpdateForm
    modal_template_name = "currencies/components/update_modal.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(
            WorkspacePermissions.CHANGE_WORKSPACE_CURRENCY, self.workspace
        ):
            return permission_denied_view(
                request,
                "You do not have permission to update exchange rates for this workspace.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_workspace_exchange_rates(
            organization=self.organization, workspace=self.workspace
        )

    def get_post_url(self):
        return reverse_lazy(
            "workspace_exchange_rate_update",
            kwargs={
                "organization_id": self.organization.pk,
                "workspace_id": self.workspace.pk,
                "pk": self.exchange_rate.pk,
            },
        )

    def get_exchange_rate_level(self):
        return "workspace"

    def get_modal_title(self):
        return "Update Exchange Rate"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "exchange_rates"
        return context

    def form_valid(self, form):
        from .services import update_workspace_exchange_rate

        try:
            update_workspace_exchange_rate(
                workspace_exchange_rate=self.exchange_rate,
                note=form.cleaned_data["note"],
                is_approved=form.cleaned_data["is_approved"],
                org_member=self.org_member,
            )
        except Exception as e:
            messages.error(self.request, e.message)
            return self._render_htmx_error_response(form)
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        row_html = render_to_string(
            "currencies/partials/row.html", context=base_context, request=self.request
        )

        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )

        response = HttpResponse(f"{message_html}<table>{row_html}</table>")
        response["HX-trigger"] = "success"
        return response


class WorkspaceExchangeRateDetailView(BaseDetailView):
    model = WorkspaceExchangeRate
    template_name = "currencies/components/detail_modal.html"
    context_object_name = EXCHANGE_RATE_DETAIL_CONTEXT_OBJECT_NAME


class WorkspaceExchangeRateDeleteView(
    WorkspaceExchangeRateRequiredMixin,
    WorkspaceRequiredMixin,
    ExchangeRateUrlIdentifierMixin,
    BaseDeleteView,
):
    model = WorkspaceExchangeRate

    def get_queryset(self):
        return get_workspace_exchange_rates(
            organization=self.organization, workspace=self.workspace
        )

    def get_exchange_rate_level(self):
        return "workspace"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(
            WorkspacePermissions.DELETE_WORKSPACE_CURRENCY, self.workspace
        ):
            return permission_denied_view(
                request,
                "You do not have permission to delete exchange rates from this workspace.",
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        print(f"\n\n\nDeleting exchange rate: {self.exchange_rate}")
        from .services import delete_workspace_exchange_rate

        try:
            delete_workspace_exchange_rate(
                workspace_exchange_rate=self.exchange_rate,
            )
        except Exception as e:
            messages.error(self.request, f"Failed to delete entry: {str(e)}")
            return self._render_htmx_error_response(form)

        messages.success(self.request, "Entry deleted successfully")
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        workspace_exchanage_rates = self.get_queryset()
        table_context = get_paginated_context(
            queryset=workspace_exchanage_rates,
            context=base_context,
            object_name=EXCHANGE_RATE_CONTEXT_OBJECT_NAME,
        )

        table_html = render_to_string(
            "currencies/partials/table.html",
            context=table_context,
            request=self.request,
        )
        message_html = render_to_string(
            "includes/message.html", context=base_context, request=self.request
        )

        response = HttpResponse(f"{message_html}{table_html}")
        return response
