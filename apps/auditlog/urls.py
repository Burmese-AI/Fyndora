from django.urls import path
from .views import auditlog_list_view, audit_detail_view

urlpatterns = [
    path("", auditlog_list_view, name="auditlog_list"),
    path("<uuid:audit_log_id>/detail/", audit_detail_view, name="audit_detail"),
]
