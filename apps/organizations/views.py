from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from apps.organizations.models import Organization, OrganizationMember
from apps.organizations.selectors import (
    get_user_organizations,
    get_organization_members_count,
    get_workspaces_count,
    get_teams_count,
)
from apps.organizations.forms import OrganizationForm
from django.shortcuts import render
from django.contrib import messages
from apps.organizations.services import create_organization_with_owner
from apps.core.constants import PAGINATION_SIZE
from django.shortcuts import get_object_or_404
from typing import Any
from django.core.paginator import Paginator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.core.constants import PAGINATION_SIZE_GRID
from apps.organizations.services import update_organization_from_form


# Create your views here.
def dashboard_view(request, organization_id):
    try:
        organization = Organization.objects.get(organization_id=organization_id)
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
    except Exception as e:
        messages.error(request, "Unable to load dashboard. Please try again later.")
        return render(request, "organizations/dashboard.html", {"organization": None})


@login_required
def home_view(request):
    try:
        organizations = get_user_organizations(request.user)
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
        if request.headers.get("HX-Request"):
            template = "organizations/partials/organization_list.html"
        else:
            template = "organizations/home.html"

        return render(request, template, context)
    except Exception as e:
        messages.error(request, "An error occurred while loading organizations")
        return render(request, "organizations/home.html", {"organizations": []})


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
                print("it good heere")
                print(form.errors)
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
        print(e)
        messages.error(request, "An error occurred while creating organization. Please try again later.")
        return render(request, "organizations/partials/create_organization_form.html", {"form": form})

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
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        query = OrganizationMember.objects.filter(organization=self.organization)
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



def settings_view(request, organization_id):
    try:
        organization = get_object_or_404(Organization, pk=organization_id)
        print(organization)
        owner = organization.owner.user if organization.owner else None
        context = {
            "organization": organization,
            "owner": owner,
        }
        return render(request, "organizations/settings.html", context)
    except Exception as e:
        messages.error(request, "An error occurred while loading settings. Please try again later.")
        return render(request, "organizations/settings.html", {"organization": None})
    

def edit_organization_view(request, organization_id):
    try:
        organization = get_object_or_404(Organization, organization_id=organization_id)
        if request.method == "POST":
            form = OrganizationForm(request.POST, instance=organization)
            if form.is_valid():
                update_organization_from_form(form=form, organization=organization)
                organization = get_object_or_404(Organization, pk=organization_id)
                print(organization)
                print(f"{organization} newly edited value")
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
                    "organizations/partials/setting_content.html", context, request=request
                )
               
               
                response = HttpResponse(f"{message_template} {setting_content_template}")
                response["HX-Trigger"] = "success"
                return response
            else:
                messages.error(request, "Please correct the errors below.")
                print("it good heere and org is ", organization)
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
            return render(request, "organizations/partials/edit_organization_form.html", {"form": form})
           
    except Exception as e:
        print(e)
        messages.error(request, "An error occurred while updating organization. Please try again later.")
        return render(request, "organizations/partials/edit_organization_form.html", {"form": form})
   