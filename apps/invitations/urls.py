from django.urls import path
from .views import accept_invitation_view, open_invitation_create_modal

urlpatterns = [
    path("<uuid:invitation_token>/", accept_invitation_view, name="accept_invitation"),
    path("modal/", open_invitation_create_modal, name="invitation_create_modal"),
]
