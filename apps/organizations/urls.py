from django.urls import path
from apps.organizations.views import HomeView
from apps.invitations.views import InvitationCreateView, InvitationListView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path('<uuid:organization_id>/invitations/', InvitationListView.as_view(), name='invitation_list'),
    path('<uuid:organization_id>/invitations/create/', InvitationCreateView.as_view(), name='invitation_create'),
]
