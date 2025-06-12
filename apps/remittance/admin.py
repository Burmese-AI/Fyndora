from django.contrib import admin
from .models import Remittance


@admin.register(Remittance)
class RemittanceAdmin(admin.ModelAdmin):
    list_display = [
        "remittance_id",
        "workspace_team",
        "due_amount",
        "paid_amount",
        "status",
        "due_date",
        "created_at",
    ]
    list_filter = [
        "status",
        "created_at",
    ]
    search_fields = [
        "remittance_id",
        "workspace_team__workspace__title",
        "workspace_team__team__name",
    ]
    readonly_fields = [
        "remittance_id",
        "created_at",
        "updated_at",
        "due_date",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("remittance_id", "workspace_team", "status")},
        ),
        ("Financial Details", {"fields": ("due_amount", "paid_amount")}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at", "due_date"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("workspace_team__workspace", "workspace_team__team")
        )
