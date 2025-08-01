from django.urls import path

from apps.organizations.views import (
    dashboard_view,
    OrganizationMemberListView,
    home_view,
    create_organization_view,
    organization_overview_view,
    settings_view,
    edit_organization_view,
    delete_organization_view,
    OrganizationExchangeRateCreateView,
    OrganizationExchangeRateUpdateView,
    OrganizationExchangeRateDetailView,
    OrganizationExchangerateDeleteView,
)
from apps.invitations.views import InvitationCreateView, InvitationListView


urlpatterns = [
    path("", home_view, name="home"),
    path("create/", create_organization_view, name="create_organization"),
    path(
        "<uuid:organization_id>/overview/",
        organization_overview_view,
        name="organization_overview",
    ),
    path(
        "<uuid:organization_id>/invitations/create/",
        InvitationCreateView.as_view(),
        name="invitation_create",
    ),
    path("dashboard/<uuid:organization_id>/", dashboard_view, name="dashboard"),
    path(
        "<uuid:organization_id>/members",
        OrganizationMemberListView.as_view(),
        name="organization_member_list",
    ),
    path(
        "<uuid:organization_id>/invitations/",
        InvitationListView.as_view(),
        name="invitation_list",
    ),
    path("<uuid:organization_id>/settings/", settings_view, name="settings"),
    path(
        "<uuid:organization_id>/settings/edit/",
        edit_organization_view,
        name="edit_organization",
    ),
    path(
        "<uuid:organization_id>/settings/delete/",
        delete_organization_view,
        name="delete_organization",
    ),
    path(
        "<uuid:organization_id>/exchange_rates/create/",
        OrganizationExchangeRateCreateView.as_view(),
        name="organization_exchange_rate_create",
    ),
    path(
        "<uuid:organization_id>/exchange_rates/<uuid:pk>/update/",
        OrganizationExchangeRateUpdateView.as_view(),
        name="organization_exchange_rate_update",
    ),
    path(
        "<uuid:organization_id>/exchange_rates/<uuid:pk>/detail/",
        OrganizationExchangeRateDetailView.as_view(),
        name="organization_exchange_rate_detail",
    ),
    path(
        "<uuid:organization_id>/exchange_rates/<uuid:pk>/delete/",
        OrganizationExchangerateDeleteView.as_view(),
        name="organization_exchange_rate_delete",
    ),
]
