from django.urls import path
from .views import delete_attachment_view, download_attachment

urlpatterns = [
    path(
        "<uuid:attachment_id>/delete/",
        delete_attachment_view,
        name="delete_attachment",
    ),
    path(
        "<uuid:attachment_id>/download/",
        download_attachment,
        name="download_attachment",
    ),
]
