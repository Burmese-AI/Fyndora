import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import baseModel
from apps.entries.constants import ENTRY_STATUS_CHOICES, ENTRY_TYPE_CHOICES
from apps.teams.constants import TeamMemberRole
from apps.teams.models import TeamMember


class Entry(baseModel):
    entry_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submitted_by = models.ForeignKey(
        TeamMember,
        on_delete=models.PROTECT,
        related_name="submitted_entries",
        limit_choices_to={"role": TeamMemberRole.SUBMITTER},
        help_text="Must be a user with Submitter role",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=ENTRY_STATUS_CHOICES, default="pending_review"
    )
    reviewed_by = models.ForeignKey(
        TeamMember,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_entries",
        limit_choices_to={
            "role__in": [
                TeamMemberRole.WORKSPACE_ADMIN,
                TeamMemberRole.OPERATIONS_REVIEWER,
                TeamMemberRole.TEAM_COORDINATOR,
            ]
        },
        help_text="Must be a Team Coordinator, Operations Reviewer, or Workspace Admin",
    )
    review_notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "entry"
        verbose_name_plural = "entries"
        ordering = ["-submitted_at"]

    def clean(self):
        super().clean()
        # Validate reviewed_by role
        if self.reviewed_by and self.reviewed_by.role not in [
            TeamMemberRole.WORKSPACE_ADMIN,
            TeamMemberRole.OPERATIONS_REVIEWER,
            TeamMemberRole.TEAM_COORDINATOR,
        ]:
            raise ValidationError(
                {
                    "reviewed_by": "Reviewer must be a Team Coordinator, Operations Reviewer, or Workspace Admin."
                }
            )

        # Validate submitted_by role
        if self.submitted_by.role != TeamMemberRole.SUBMITTER:
            raise ValidationError(
                {"submitted_by": "Only users with Submitter role can create entries."}
            )

    def __str__(self):
        return (
            f"{self.entry_id} - {self.submitted_by} - {self.entry_type} - {self.amount}"
        )
