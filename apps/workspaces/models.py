from django.db import models
from apps.core.models import baseModel
from apps.organizations.models import Organization, OrganizationMember
import uuid
from apps.workspaces.constants import StatusChoices
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.teams.models import Team
from django.core.exceptions import ValidationError


# Create your models here.
class Workspace(baseModel):
    workspace_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="workspaces"
    )
    workspace_admin = models.ForeignKey(
        OrganizationMember,
        on_delete=models.SET_NULL,
        related_name="administered_workspaces",
        null=True,
        blank=True,
    )  # This is the admin of the workspace, it can be null if the workspace is not yet administered and will be assigned later.
    title = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        OrganizationMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_workspaces",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )
    remittance_rate = models.DecimalField(
        max_digits=5,  # 0.00 - 100.00
        decimal_places=2,
        default=90.00,
        help_text="% obligation from entries (Default 90%)",
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    expense = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Collection of Teams Expense + Direct Expense from the Workspace Admin",
    )

    class Meta:
        verbose_name = "workspace"
        verbose_name_plural = "workspaces"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "title"],
                name="unique_workspace_in_organization",
            )
        ]

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError("Start date must be before end date.")

    def __str__(self):
        return f"{self.title} ({self.organization.title})"


class WorkspaceTeam(baseModel):
    workspace_team_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="workspace_teams"
    )
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="workspace_teams"
    )

    class Meta:
        verbose_name = "workspace team"
        verbose_name_plural = "workspace teams"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "workspace"], name="unique_team_in_workspace"
            )
        ]

    def __str__(self):
        return f"{self.team.title} in {self.workspace.title}"
