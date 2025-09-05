from django.urls import path
from .views import auditlog_list_view

urlpatterns = [
    path("", auditlog_list_view, name="auditlog_list"),
]
