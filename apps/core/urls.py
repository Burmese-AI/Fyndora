from django.urls import path
from .views import close_modal

urlpatterns = [
    path("close-modal/", close_modal, name="close_modal"),
]
