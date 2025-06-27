from django.db import models
from apps.core.models import baseModel
from apps.organizations.models import OrganizationMember
import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.teams.constants import TeamMemberRole
from apps.organizations.models import Organization


class Team(baseModel):
    team_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="teams",
    )
    title = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    team_coordinator = models.ForeignKey(
        OrganizationMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coordinated_teams",
    )
    custom_remittance_rate = models.DecimalField(
        max_digits=5,  # 0.00 - 100.00
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text="Overrides workspace default if set (percentage value between 0 and 100)",
    )
    created_by = models.ForeignKey(
        OrganizationMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_teams",
    )

    class Meta:
        verbose_name = "team"
        verbose_name_plural = "teams"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["title", "organization"], name="unique_team"
            )
        ]

    def __str__(self):
        return f"{self.title}"


class TeamMember(baseModel):
    team_member_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization_member = models.ForeignKey(
        "organizations.OrganizationMember",
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="members")
    role = models.CharField(
        max_length=32, choices=TeamMemberRole.choices, default=TeamMemberRole.SUBMITTER
    )

    class Meta:
        verbose_name = "team member"
        verbose_name_plural = "team members"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "organization_member"], name="unique_team_member"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization_member} in {self.team}"
