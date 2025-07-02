from django.urls import path
from .views import delete_attachment_view

urlpatterns = [
    path(
        "<uuid:attachment_id>/delete/",
        delete_attachment_view,
        name="delete_attachment",
    ),
]
