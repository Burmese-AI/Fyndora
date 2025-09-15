from datetime import timedelta

from django.contrib import admin, messages
from django.db import models
from django.shortcuts import render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from .config import AuditConfig
from .constants import AuditActionType
from .models import AuditTrail
from .selectors import get_retention_summary
from .services import audit_cleanup_expired_logs


class ExpiredFilter(admin.SimpleListFilter):
    """Custom filter to show expired vs active logs."""

    title = "retention status"
    parameter_name = "expired"

    def lookups(self, request, model_admin):
        return (
            ("expired", "Expired"),
            ("active", "Active"),
        )

    def queryset(self, request, queryset):
        if self.value() == "expired":
            now = timezone.now()

            # Get authentication logs that are expired
            auth_actions = [
                AuditActionType.LOGIN_SUCCESS,
                AuditActionType.LOGIN_FAILED,
                AuditActionType.LOGOUT,
            ]
            auth_cutoff = now - timedelta(
                days=AuditConfig.AUTHENTICATION_RETENTION_DAYS
            )

            # Get default logs that are expired
            default_cutoff = now - timedelta(days=AuditConfig.DEFAULT_RETENTION_DAYS)

            # Return expired logs
            return queryset.filter(
                models.Q(action_type__in=auth_actions, timestamp__lt=auth_cutoff)
                | models.Q(timestamp__lt=default_cutoff).exclude(
                    action_type__in=auth_actions
                )
            )

        elif self.value() == "active":
            now = timezone.now()

            # Get authentication logs that are active
            auth_actions = [
                AuditActionType.LOGIN_SUCCESS,
                AuditActionType.LOGIN_FAILED,
                AuditActionType.LOGOUT,
            ]
            auth_cutoff = now - timedelta(
                days=AuditConfig.AUTHENTICATION_RETENTION_DAYS
            )

            # Get default logs that are active
            default_cutoff = now - timedelta(days=AuditConfig.DEFAULT_RETENTION_DAYS)

            # Return active logs
            return queryset.filter(
                models.Q(action_type__in=auth_actions, timestamp__gte=auth_cutoff)
                | models.Q(timestamp__gte=default_cutoff).exclude(
                    action_type__in=auth_actions
                )
            )

        return queryset


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = [
        "audit_id",
        "action_type",
        "target_entity_type",
        "target_entity",
        "user",
        "timestamp",
        "is_expired_display",
        "organization",
        "workspace",
    ]
    list_filter = [
        "action_type",
        "target_entity_type",
        "timestamp",
        ExpiredFilter,
    ]
    search_fields = [
        "audit_id",
        "target_entity",
        "user__username",
        "user__email",
    ]
    readonly_fields = [
        "audit_id",
        "timestamp",
        "is_expired_display",
    ]
    ordering = ["-timestamp"]
    actions = ["cleanup_expired_logs_action"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("audit_id", "user", "action_type", "timestamp")},
        ),
        ("Target Information", {"fields": ("target_entity", "target_entity_type")}),
        (
            "Additional Details",
            {"fields": ("metadata", "details"), "classes": ("collapse",)},
        ),
        (
            "Retention Information",
            {"fields": ("is_expired_display",), "classes": ("collapse",)},
        ),
    )

    def is_expired_display(self, obj):
        """Display whether the log is expired with color coding."""
        if obj.is_expired():
            return format_html(
                '<span style="color: red; font-weight: bold;">Expired</span>'
            )
        return format_html('<span style="color: green;">Active</span>')

    is_expired_display.short_description = "Retention Status"

    def cleanup_expired_logs_action(self, request, queryset):
        """Admin action to cleanup expired logs."""
        stats = audit_cleanup_expired_logs(dry_run=False)

        message = (
            f"Cleanup completed. Deleted {stats['total_deleted']} logs "
            f"(Auth: {stats['authentication_deleted']}, "
            f"Default: {stats['default_deleted']})"
        )

        self.message_user(request, message, messages.SUCCESS)

    cleanup_expired_logs_action.short_description = "Clean up expired audit logs"

    def get_urls(self):
        """Add custom admin URLs for retention management."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "retention-summary/",
                self.admin_site.admin_view(self.retention_summary_view),
                name="auditlog_retention_summary",
            ),
        ]
        return custom_urls + urls

    def retention_summary_view(self, request):
        """Custom admin view for retention summary."""
        summary = get_retention_summary()

        context = {
            "title": "Audit Log Retention Summary",
            "summary": summary,
            "opts": self.model._meta,
            "has_view_permission": True,
        }

        return render(request, "admin/auditlog/retention_summary.html", context)
