from django.db import models
from django.core.exceptions import ValidationError
from apps.core.models import baseModel
import uuid
from apps.remittance.constants import STATUS_CHOICES

class Remittance(baseModel):
    remittance_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace_team = models.ForeignKey(
        "workspaces.WorkspaceTeam",
        on_delete=models.PROTECT,
        related_name="remittances"
    )
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
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

    def clean(self):
        """
        Validate the remittance model.
        - Ensure workspace has an end_date
        - Ensure amounts are non-negative
        - Ensure paid_amount doesn't exceed due_amount
        """
        if not self.workspace.end_date:
            raise ValidationError(
                "Cannot create remittance: The workspace must have an end_date set."
            )
            
        if hasattr(self, 'workspace_team') and self.workspace_team:
            if not self.workspace_team.workspace == self.workspace:
                raise ValidationError(
                    "The selected team is not part of this workspace."
                )
        
        if self.due_amount < 0:
            raise ValidationError("Due amount cannot be negative.")
        
        if self.paid_amount < 0:
            raise ValidationError("Paid amount cannot be negative.")
        
        if self.paid_amount > self.due_amount:
            raise ValidationError("Paid amount cannot exceed due amount.")
        
        super().clean()

    def __str__(self):
        return f"Remittance {self.remittance_id} - {self.workspace.title} (Status: {self.get_status_display()})"
