from django.urls import path
from .views import delete_attachment

urlpatterns = [
    path(
        "<uuid:attachment_id>/delete/",
        delete_attachment,
        name="delete_attachment",
    ),
]