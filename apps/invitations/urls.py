from django.urls import path, include
from .views import accept_invitation

urlpatterns = [
    path("<uuid:invitation_token>/", accept_invitation, name="accept_invitation")
]
