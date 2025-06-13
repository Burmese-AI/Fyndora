import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import baseModel
from apps.remittance.constants import STATUS_CHOICES

User = get_user_model()


class Remittance(baseModel):
    remittance_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    workspace_team = models.ForeignKey(
        "workspaces.WorkspaceTeam", on_delete=models.PROTECT, related_name="remittances"
    )
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_remittances",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    @property
    def workspace(self):
        """For backward compatibility and easier access to workspace."""
        return self.workspace_team.workspace

    class Meta:
        verbose_name = "remittance"
        verbose_name_plural = "remittances"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    @property
    def due_date(self):
        """Return the workspace's end_date as the due_date."""
        return self.workspace.end_date

    def update_status(self):
        """
        Update remittance status based on payment and confirmation.
        """
        # A paid remittance status is final and should not be reverted by this method.
        if self.status == "paid" and self.pk:
            return

        # Overdue status takes precedence over others, except for 'paid'.
        if (
            self.due_date
            and self.due_date < timezone.now().date()
            and self.paid_amount < self.due_amount
        ):
            self.status = "overdue"
            return

        if self.paid_amount >= self.due_amount and self.confirmed_by is not None:
            self.status = "paid"
        elif self.paid_amount > 0:
            self.status = "partial"
        else:
            self.status = "pending"

    def clean(self):
        """
        Validate the remittance model.
        - Ensure workspace has an end_date
        - Ensure amounts are non-negative
        - Ensure paid_amount doesn't exceed due_amount
        """
        if hasattr(self, "workspace_team") and self.workspace_team:
            if not self.workspace.end_date:
                raise ValidationError(
                    "Cannot create remittance: The workspace must have an end_date set."
                )

        if self.due_amount < 0 or self.paid_amount < 0:
            raise ValidationError("Amounts cannot be negative.")

        if self.paid_amount > self.due_amount:
            raise ValidationError("Paid amount cannot exceed the due amount.")

    def save(self, *args, **kwargs):
        """Save the remittance and update the status."""
        self.update_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Remittance {self.remittance_id} - {self.workspace.title} (Status: {self.get_status_display()})"
