from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from apps.organizations.models import (
    Organization,
    OrganizationMember,
    OrganizationExchangeRate,
)
from apps.organizations.selectors import (
    get_user_organizations,
    get_organization_members_count,
    get_workspaces_count,
    get_teams_count,
    get_org_exchange_rates,
)
from apps.organizations.forms import (
    OrganizationForm,
    OrganizationExchangeRateCreateForm,
    OrganizationExchangeRateUpdateForm,
)
from django.shortcuts import render
from django.contrib import messages
from apps.organizations.services import create_organization_with_owner
from apps.core.constants import PAGINATION_SIZE
from django.shortcuts import get_object_or_404
from typing import Any
from django.core.paginator import Paginator
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from apps.core.constants import PAGINATION_SIZE_GRID
from apps.organizations.services import update_organization_from_form
from django_htmx.http import HttpResponseClientRedirect
from apps.core.views.crud_base_views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseUpdateView,
)
from apps.core.views.base_views import BaseGetModalFormView
from apps.core.views.mixins import OrganizationRequiredMixin, UpdateFormMixin
from apps.core.utils import get_paginated_context
from apps.organizations.mixins.organization_exchange_rate.required_mixins import (
    OrganizationExchangeRateRequiredMixin,
)
from apps.currencies.views.mixins import ExchangeRateUrlIdentifierMixin
from apps.currencies.constants import (
    EXCHANGE_RATE_CONTEXT_OBJECT_NAME,
    EXCHANGE_RATE_DETAIL_CONTEXT_OBJECT_NAME,
)
from apps.core.permissions import OrganizationPermissions
from apps.core.utils import permission_denied_view
from apps.organizations.selectors import get_organization_by_id
from apps.core.utils import can_manage_organization
from apps.core.utils import (
    revoke_workspace_admin_permission,
    revoke_operations_reviewer_permission,
    revoke_team_coordinator_permission,
    revoke_workspace_team_member_permission,
)


# Create your views here.
@login_required
def dashboard_view(request, organization_id):
    try:
        organization = get_organization_by_id(organization_id)
        if not can_manage_organization(request.user, organization):
            return permission_denied_view(
                request,
                "You do not have permission to access this organization.",
            )
        members_count = get_organization_members_count(organization)
        workspaces_count = get_workspaces_count(organization)
        teams_count = get_teams_count(organization)
        owner = organization.owner.user if organization.owner else None
        context = {
            "organization": organization,
            "members_count": members_count,
            "workspaces_count": workspaces_count,
            "teams_count": teams_count,
            "owner": owner,
        }
        return render(request, "organizations/dashboard.html", context)
    except Exception:
        messages.error(request, "Unable to load dashboard. Please try again later.")
        return render(request, "organizations/dashboard.html", {"organization": None})


@login_required
def home_view(request):
    try:
        organizations = get_user_organizations(request.user)
        for organization in organizations:
            organization.permissions = {
                "can_manage_organization": can_manage_organization(
                    request.user, organization
                ),
            }
        paginator = Paginator(organizations, PAGINATION_SIZE_GRID)
        page = request.GET.get("page", 1)

        try:
            organizations = paginator.page(page)
        except PageNotAnInteger:
            organizations = paginator.page(1)
        except EmptyPage:
            organizations = paginator.page(paginator.num_pages)

        context = {
            "organizations": organizations,
            "is_paginated": organizations.paginator.num_pages > 1,
            "page_obj": organizations,
            "paginator": paginator,
        }

        template = "organizations/home.html"

        return render(request, template, context)
    except Exception as e:
        print(f"Exception in home_view: {e}")
        messages.error(request, "An error occurred while loading organizations")
        return render(request, "organizations/home.html", {"organizations": []})


@login_required
def create_organization_view(request):
    try:
        if request.method != "POST":
            form = OrganizationForm()
            return render(
                request,
                "organizations/partials/create_organization_form.html",
                {"form": form},
            )
        else:
            form = OrganizationForm(request.POST)
            if form.is_valid():
                create_organization_with_owner(form=form, user=request.user)
                organizations = get_user_organizations(request.user)
                # for UI purposes
                for organization in organizations:
                    organization.permissions = {
                        "can_manage_organization": can_manage_organization(
                            request.user, organization
                        ),
                    }
                paginator = Paginator(organizations, PAGINATION_SIZE_GRID)
                page = request.GET.get("page", 1)
                organizations = paginator.page(page)

                context = {
                    "organizations": organizations,
                    "is_paginated": organizations.paginator.num_pages > 1,
                    "page_obj": organizations,
                    "paginator": paginator,
                    "is_oob": True,
                }
                messages.success(request, "Organization created successfully!")
                organizations_template = render_to_string(
                    "organizations/partials/organization_list.html",
                    context,
                    request=request,
                )
                message_template = render_to_string(
                    "includes/message.html", context, request=request
                )
                response = HttpResponse(f"{message_template} {organizations_template}")
                response["HX-Trigger"] = "success"
                return response
            else:
                messages.error(request, "Organization creation failed")
                context = {"form": form, "is_oob": True}
                form_template = render_to_string(
                    "organizations/partials/create_organization_form.html",
                    context,
                    request=request,
                )
                message_template = render_to_string(
                    "includes/message.html", context, request=request
                )
                response = HttpResponse(f"{message_template} {form_template}")
                return response
    except Exception as e:
        print(f"Exception in create_organization_view: {e}")
        messages.error(
            request,
            "An error occurred while creating organization. Please try again later.",
        )
        form = OrganizationForm()  # Create a new form instance for the error case
        return render(
            request,
            "organizations/partials/create_organization_form.html",
            {"form": form},
        )


@login_required
def organization_overview_view(request, organization_id):
    organization = get_object_or_404(Organization, pk=organization_id)
    owner = organization.owner.user if organization.owner else None
    members = get_organization_members_count(organization)
    workspaces = get_workspaces_count(organization)
    teams = get_teams_count(organization)
    context = {
        "organization": organization,
        "members": members,
        "workspaces": workspaces,
        "teams": teams,
        "owner": owner,
    }
    return render(request, "organizations/organization_overview.html", context)


class OrganizationMemberListView(LoginRequiredMixin, ListView):
    model = OrganizationMember
    template_name = "organization_members/index.html"
    context_object_name = "members"
    paginate_by = PAGINATION_SIZE

    def dispatch(self, request, *args, **kwargs):
        # Get ORG ID from URL
        organization_id = self.kwargs["organization_id"]
        self.organization = get_object_or_404(Organization, pk=organization_id)
        if not can_manage_organization(request.user, self.organization):
            return permission_denied_view(
                request,
                "You do not have permission to access this organization.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        #list down all members except the owner to prevent the owner from being deleted
        query = OrganizationMember.objects.filter(organization=self.organization).exclude(user=self.organization.owner.user)
        return query

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view"] = "members"
        context["organization"] = self.organization
        return context

    def render_to_response(self, context: dict[str, Any], **response_kwargs: Any):
        if self.request.htmx:
            return render(
                self.request, "organization_members/partials/table.html", context
            )
        return super().render_to_response(context, **response_kwargs)


@login_required
def settings_view(request, organization_id):
    try:
        organization = get_object_or_404(Organization, pk=organization_id)

        owner = organization.owner.user if organization.owner else None
        context = {
            "organization": organization,
            "owner": owner,
        }
        if not can_manage_organization(request.user, organization):
            return permission_denied_view(
                request,
                "You do not have permission to access this organization.",
            )

        org_exchanage_rates = get_org_exchange_rates(organization=organization)
        context = get_paginated_context(
            queryset=org_exchanage_rates,
            context=context,
            object_name=EXCHANGE_RATE_CONTEXT_OBJECT_NAME,
        )
        context["url_identifier"] = "organization"
        context["permissions"] = {
            "can_add_org_exchange_rate": request.user.has_perm(
                OrganizationPermissions.ADD_ORG_CURRENCY, organization
            ),
            "can_change_org_exchange_rate": request.user.has_perm(
                OrganizationPermissions.CHANGE_ORG_CURRENCY, organization
            ),
            "can_delete_org_exchange_rate": request.user.has_perm(
                OrganizationPermissions.DELETE_ORG_CURRENCY, organization
            ),
            "can_change_organization": request.user.has_perm(
                OrganizationPermissions.CHANGE_ORGANIZATION, organization
            ),
            "can_delete_organization": request.user.has_perm(
                OrganizationPermissions.DELETE_ORGANIZATION, organization
            ),
        }
        return render(request, "organizations/settings.html", context)
    except Exception:
        messages.error(
            request, "An error occurred while loading settings. Please try again later."
        )
        return render(request, "organizations/settings.html", {"organization": None})


@login_required
def edit_organization_view(request, organization_id):
    try:
        organization = get_object_or_404(Organization, organization_id=organization_id)

        if not request.user.has_perm("change_organization", organization):
            messages.error(
                request, "You do not have permission to edit this organization."
            )
            return HttpResponseClientRedirect("/403")

        if request.method == "POST":
            form = OrganizationForm(request.POST, instance=organization)
            if form.is_valid():
                update_organization_from_form(form=form, organization=organization)
                organization = get_object_or_404(Organization, pk=organization_id)
                owner = organization.owner.user if organization.owner else None
                messages.success(request, "Organization updated successfully!")
                context = {
                    "organization": organization,
                    "is_oob": True,
                    "owner": owner,
                }
                message_template = render_to_string(
                    "includes/message.html", context, request=request
                )
                setting_content_template = render_to_string(
                    "organizations/partials/setting_content.html",
                    context,
                    request=request,
                )

                response = HttpResponse(
                    f"{message_template} {setting_content_template}"
                )
                response["HX-Trigger"] = "success"
                return response
            else:
                messages.error(request, "Please correct the errors below.")
                context = {
                    "form": form,
                    "is_oob": True,
                    "organization": organization,
                }
                form_template = render_to_string(
                    "organizations/partials/edit_organization_form.html",
                    context,
                    request=request,
                )
            message_template = render_to_string(
                "includes/message.html", context, request=request
            )
            response = HttpResponse(f"{message_template} {form_template}")
            return response
        else:
            form = OrganizationForm(instance=organization)
            return render(
                request,
                "organizations/partials/edit_organization_form.html",
                {"form": form},
            )

    except Exception as e:
        print(e)
        messages.error(
            request,
            "An error occurred while updating organization. Please try again later.",
        )
        return render(
            request,
            "organizations/partials/edit_organization_form.html",
            {"form": form},
        )


@login_required
def delete_organization_view(request, organization_id):
    try:
        organization = get_object_or_404(Organization, pk=organization_id)
        if not request.user.has_perm("delete_organization", organization):
            messages.error(
                request, "You do not have permission to delete this organization."
            )
            return HttpResponseClientRedirect("/403")

        if request.method == "POST":
            organization.delete()
            messages.success(request, "Organization deleted successfully.")
            response = HttpResponse()
            # Client-side redirect
            response['HX-Redirect'] = '/'
            return response
        else:
            return render(
                request,
                "organizations/partials/delete_organization_form.html",
                {"organization": organization},
            )
    except Exception as e:
        messages.error(
            request,
            "An error occurred while deleting organization. Please try again later.",
        )
        context = {
            "is_oob": True,
        }
        message_html = render_to_string(
            "includes/message.html", context=context, request=request
        )

        return HttpResponse(f"{message_html}")
        


class OrganizationExchangeRateCreateView(
    OrganizationRequiredMixin,
    ExchangeRateUrlIdentifierMixin,
    BaseGetModalFormView,
    BaseCreateView,
):
    model = OrganizationExchangeRate
    form_class = OrganizationExchangeRateCreateForm
    modal_template_name = "currencies/components/create_modal.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(
            OrganizationPermissions.ADD_ORG_CURRENCY, self.organization
        ):
            return permission_denied_view(
                request,
                "You do not have permission to add exchange rates to this organization.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_org_exchange_rates(organization=self.organization)

    def get_post_url(self):
        return reverse_lazy(
            "organization_exchange_rate_create",
            kwargs={"organization_id": self.organization.pk},
        )

    def get_modal_title(self):
        return "Add Exchange Rate"

    def get_exchange_rate_level(self):
        return "organization"

    def form_valid(self, form):
        from .services import create_organization_exchange_rate

        try:
            create_organization_exchange_rate(
                organization=self.organization,
                organization_member=self.org_member,
                currency_code=form.cleaned_data["currency_code"],
                rate=form.cleaned_data["rate"],
                effective_date=form.cleaned_data["effective_date"],
                note=form.cleaned_data["note"],
            )
        except Exception as e:
            messages.error(self.request, f"Failed to create Exchange Rate: {str(e)}")
            return self._render_htmx_error_response(form)

        messages.success(self.request, "Entry created successfully")
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        org_exchanage_rates = self.get_queryset()
        table_context = get_paginated_context(
            queryset=org_exchanage_rates,
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


class OrganizationExchangeRateUpdateView(
    ExchangeRateUrlIdentifierMixin,
    OrganizationExchangeRateRequiredMixin,
    OrganizationRequiredMixin,
    UpdateFormMixin,
    BaseGetModalFormView,
    BaseUpdateView,
):
    model = OrganizationExchangeRate
    form_class = OrganizationExchangeRateUpdateForm
    modal_template_name = "currencies/components/update_modal.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(
            OrganizationPermissions.CHANGE_ORG_CURRENCY, self.organization
        ):
            return permission_denied_view(
                request,
                "You do not have permission to change exchange rates to this organization.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_org_exchange_rates(organization=self.organization)

    def get_post_url(self):
        return reverse_lazy(
            "organization_exchange_rate_update",
            kwargs={
                "organization_id": self.organization.pk,
                "pk": self.exchange_rate.pk,
            },
        )

    def get_exchange_rate_level(self):
        return "organization"

    def get_modal_title(self):
        return "Update Exchange Rate"

    def form_valid(self, form):
        from .services import update_organization_exchange_rate

        try:
            update_organization_exchange_rate(
                organization=self.organization,
                organization_member=self.org_member,
                org_exchange_rate=self.exchange_rate,
                note=form.cleaned_data["note"],
            )
        except Exception as e:
            messages.error(self.request, f"Failed to update entry: {str(e)}")
            return self._render_htmx_error_response(form)

        messages.success(self.request, "Entry updated successfully")
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


class OrganizationExchangeRateDetailView(BaseDetailView):
    model = OrganizationExchangeRate
    template_name = "currencies/components/detail_modal.html"
    context_object_name = EXCHANGE_RATE_DETAIL_CONTEXT_OBJECT_NAME


class OrganizationExchangerateDeleteView(
    OrganizationExchangeRateRequiredMixin,
    OrganizationRequiredMixin,
    ExchangeRateUrlIdentifierMixin,
    BaseDeleteView,
):
    model = OrganizationExchangeRate

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(
            OrganizationPermissions.DELETE_ORG_CURRENCY, self.organization
        ):
            return permission_denied_view(
                request,
                "You do not have permission to delete exchange rates to this organization.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_org_exchange_rates(organization=self.organization)

    def get_exchange_rate_level(self):
        return "organization"

    def form_valid(self, form):
        from .services import delete_organization_exchange_rate

        try:
            delete_organization_exchange_rate(
                organization=self.organization,
                organization_member=self.org_member,
                org_exchange_rate=self.exchange_rate,
            )
        except Exception as e:
            messages.error(self.request, f"Failed to delete entry: {str(e)}")
            return self._render_htmx_error_response(form)

        messages.success(self.request, "Entry deleted successfully")
        return self._render_htmx_success_response()

    def _render_htmx_success_response(self) -> HttpResponse:
        base_context = self.get_context_data()

        org_exchanage_rates = self.get_queryset()
        table_context = get_paginated_context(
            queryset=org_exchanage_rates,
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


def remove_organization_member_view(request, organization_id, member_id):
    try:
        organization = get_object_or_404(Organization, pk=organization_id)
        member = get_object_or_404(OrganizationMember, pk=member_id)

        user_administered_workspaces = member.administered_workspaces.all()
        if user_administered_workspaces.count() > 0:
            # revoke workspace admin permission from every workspace that the user is admin of
            for workspace in user_administered_workspaces:
                revoke_workspace_admin_permission(member.user, workspace)
                workspace.workspace_admin = None
                workspace.save()

        user_reviewed_workspaces = member.reviewed_workspaces.all()
        if user_reviewed_workspaces.count() > 0:
            # revoke operations reviewer permission from every workspace that the user is reviewer of
            for workspace in user_reviewed_workspaces:
                revoke_operations_reviewer_permission(member.user, workspace)
                workspace.operations_reviewer = None
                workspace.save()

        user_coordinated_teams = member.coordinated_teams.all()
        if user_coordinated_teams.count() > 0:
            for team in user_coordinated_teams:
                revoke_team_coordinator_permission(member.user, team)
                team.team_coordinator = None
                team.save()

        user_joined_teams = member.team_memberships.all()
        for team_membership in user_joined_teams:
            for workspace_team in team_membership.team.joined_workspaces.all():
                revoke_workspace_team_member_permission(member.user, workspace_team)
                # if the user is in teams , remove the user from the team
                team_membership.delete()

        # after removing the permission of that user ,delete the member from the organization (should be last step,softdelete)
        member.delete()

        messages.success(request, "Organization member removed successfully.")
        return redirect("organization_member_list", organization_id=organization_id)
    except Exception:
        messages.error(
            request,
            "An error occurred while removing organization member. Please try again later.",
        )
        return redirect("organization_member_list", organization_id=organization_id)
