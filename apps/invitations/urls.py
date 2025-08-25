from django.urls import path
from .views import accept_invitation_view, cancel_invitation_view

urlpatterns = [
    path("<uuid:invitation_token>/", accept_invitation_view, name="accept_invitation"),
    path(
        "<uuid:invitation_id>/delete/",
        cancel_invitation_view,
        name="cancel_invitation",
    ),
]
