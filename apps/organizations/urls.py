from django.urls import path

from apps.organizations.views import (
    dashboard_view,
    OrganizationMemberListView,
    home_view,
    create_organization_view,
    organization_overview_view,
)
from apps.invitations.views import InvitationCreateView, InvitationListView


urlpatterns = [
    path("", home_view, name="home"),
    path("create/", create_organization_view, name="create_organization"),
    path("<uuid:organization_id>/overview/", organization_overview_view, name="organization_overview"),
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
]
