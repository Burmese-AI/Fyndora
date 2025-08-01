from django.db import models
from apps.core.models import baseModel
from apps.organizations.models import OrganizationMember
import uuid
from apps.teams.constants import TeamMemberRole
from apps.organizations.models import Organization
from apps.core.permissions import TeamPermissions


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
        permissions = [
            (TeamPermissions.ADD_TEAM_MEMBER, TeamPermissions.ADD_TEAM_MEMBER.label),
        ]
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
