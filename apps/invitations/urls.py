from django.urls import path
from .views import accept_invitation_view

urlpatterns = [
    path("<uuid:invitation_token>/", accept_invitation_view, name="accept_invitation"),
]
