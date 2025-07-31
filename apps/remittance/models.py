import uuid

from django.db import models
from django.utils import timezone

from apps.core.models import baseModel
from apps.remittance.constants import RemittanceStatus
from apps.organizations.models import OrganizationMember
from apps.workspaces.models import WorkspaceTeam
from django.core.validators import MinValueValidator


class Remittance(baseModel):
    remittance_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    workspace_team = models.OneToOneField(
        WorkspaceTeam,
        on_delete=models.CASCADE,
        related_name="remittance",
    )
    due_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)]
    )
    paid_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20,
        choices=RemittanceStatus.choices,
        default=RemittanceStatus.PENDING,
    )
    confirmed_by = models.ForeignKey(
        OrganizationMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_remittances",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    paid_within_deadlines = models.BooleanField(default=True)
    is_overpaid = models.BooleanField(default=False)
    review_notes = models.TextField(blank=True, null=True)

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
            models.Index(fields=["paid_within_deadlines"]),
        ]
        permissions = [
            ("review_remittance", "Can review and confirm remittances"),
            ("flag_remittance", "Can flag remittances"),
        ]

    def update_status(self):
        """
        Update remittance status based on paid and due amounts.
        """

        # Don't update status if it's already canceled
        if self.status == RemittanceStatus.CANCELED:
            return
            
        if self.paid_amount == 0.0:
            self.status = RemittanceStatus.PENDING
        elif self.paid_amount < self.due_amount:
            self.status = RemittanceStatus.PARTIAL
        else:
            self.status = RemittanceStatus.PAID
        print(f"Debugging status => {self.status}")

    def check_if_overdue(self):
        if (
            self.workspace_team.workspace.end_date < timezone.now().date()
            and self.status != RemittanceStatus.PAID
        ):
            if self.paid_within_deadlines:
                self.paid_within_deadlines = False

    def check_if_overpaid(self):
        self.is_overpaid = self.paid_amount > self.due_amount

    def __str__(self):
        return f"Remittance {self.remittance_id} - {self.workspace.title} (Status: {self.get_status_display()})"
