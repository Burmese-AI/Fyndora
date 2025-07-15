from django.urls import path
from .views import close_modal, permission_denied_view


urlpatterns = [
    path("close-modal/", close_modal, name="close_modal"),
    path("403/", permission_denied_view, name="permission_denied"),
]
