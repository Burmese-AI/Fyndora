from django.contrib import admin
from .models import AuditTrail


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = [
        "audit_id",
        "action_type",
        "target_entity_type",
        "target_entity",
        "user",
        "timestamp",
    ]
    list_filter = [
        "action_type",
        "target_entity_type",
        "timestamp",
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
    ]
    ordering = ["-timestamp"]

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
    )
