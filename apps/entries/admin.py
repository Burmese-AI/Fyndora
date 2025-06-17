from django.contrib import admin
# from .models import Entry


# @admin.register(Entry)
# class EntryAdmin(admin.ModelAdmin):
#     list_display = [
#         "entry_id",
#         "submitted_by",
#         "entry_type",
#         "amount",
#         "status",
#         "submitted_at",
#         "reviewed_by",
#     ]
#     list_filter = [
#         "entry_type",
#         "status",
#         "submitted_at",
#     ]
#     search_fields = [
#         "entry_id",
#         "description",
#         "submitted_by__user__username",
#         "submitted_by__user__email",
#         "reviewed_by__user__username",
#     ]
#     readonly_fields = [
#         "entry_id",
#         "submitted_at",
#     ]
#     ordering = ["-submitted_at"]

#     fieldsets = (
#         (
#             "Basic Information",
#             {"fields": ("entry_id", "entry_type", "amount", "description", "status")},
#         ),
#         ("Submission Details", {"fields": ("submitted_by", "submitted_at")}),
#         (
#             "Review Information",
#             {"fields": ("reviewed_by", "review_notes"), "classes": ("collapse",)},
#         ),
#     )

#     def get_queryset(self, request):
#         return (
#             super()
#             .get_queryset(request)
#             .select_related(
#                 "submitted_by__organization_member__user",
#                 "reviewed_by__organization_member__user",
#             )
#         )
