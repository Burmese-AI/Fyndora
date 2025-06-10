from django.db import models
from apps.core.models import baseModel
from apps.organizations.models import OrganizationMember
from apps.workspaces.models import Workspace
import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator


class Team(baseModel):
    team_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    team_coordinator = models.ForeignKey(
        OrganizationMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coordinated_teams"
    )
    custom_remittance_rate = models.DecimalField(
        max_digits=5, # 0.00 - 100.00
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Overrides workspace default if set (percentage value between 0 and 100)"
    )
    created_by = models.ForeignKey(
        OrganizationMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_teams"
    )

    class Meta:
        verbose_name = "team"
        verbose_name_plural = "teams"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["title"],
                name="unique_team"
            )
        ]

    def __str__(self):
        return f"{self.title} of {self.workspace.title}"
