import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from apps.core.models import baseModel
from apps.entries.constants import EntryType, EntryStatus
from apps.teams.constants import TeamMemberRole
from apps.teams.models import TeamMember
from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.organizations.models import OrganizationMember


class Entry(baseModel):
    entry_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Generic Foreign Key to specify the submitter
    submitter_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    submitter_object_id = models.UUIDField()
    submitter = GenericForeignKey("submitter_content_type", "submitter_object_id")
    # Specify which workspace team the entry belongs to if submitter is team member
    workspace_team = models.ForeignKey(
        WorkspaceTeam,
        on_delete=models.CASCADE,
        related_name="entries",
        null=True,
        blank=True,
    )
    # Specify which workspace this entry belongs to for any entry types
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="entries",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    is_flagged = models.BooleanField(default=False)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    description = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=EntryStatus.choices, default=EntryStatus.PENDING_REVIEW
    )
    reviewed_by = models.ForeignKey(
        OrganizationMember,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_entries",
    )
    review_notes = models.TextField(null=True, blank=True)

    @property
    def submitter_user_name(self):
        """Get the username of the submitter"""
        if isinstance(self.submitter, OrganizationMember):
            return self.submitter.user.username
        elif isinstance(self.submitter, TeamMember):
            return self.submitter.organization_member.user.username
        return None

    @property
    def is_workspace_specific(self):
        return self.entry_type == EntryType.WORKSPACE_EXP or self.workspace is not None

    @property
    def organization(self):
        """Get the organization this entry belongs to"""
        if self.workspace:
            return self.workspace.organization
        elif isinstance(self.submitter, OrganizationMember):
            return self.submitter.organization
        elif isinstance(self.submitter, TeamMember):
            return self.submitter.organization_member.organization
        return None

    def clean(self):
        super().clean()

        # 1. Reviewer cannot be the same as the submitter
        if self.reviewed_by and self.submitter:
            if (
                isinstance(self.submitter, OrganizationMember)
                and self.reviewed_by == self.submitter
            ) or (
                isinstance(self.submitter, TeamMember)
                and self.reviewed_by == self.submitter.organization_member
            ):
                raise ValidationError(
                    "Reviewer and submitter cannot be the same person."
                )

        # 2. Auditors are not allowed to submit entries
        if isinstance(self.submitter, TeamMember):
            if self.submitter.role == TeamMemberRole.AUDITOR:
                raise ValidationError("Auditors are not allowed to submit entries.")

        # 3. Reviewer must belong to the same organization as the entry
        if self.reviewed_by and self.organization:
            if self.reviewed_by.organization != self.organization:
                raise ValidationError(
                    "Reviewer must belong to the same organization as the entry."
                )

        # 4. Submitter must belong to the team linked to this Workspace Team
        if isinstance(self.submitter, TeamMember) and self.workspace_team:
            if self.submitter.team != self.workspace_team.team:
                raise ValidationError(
                    "Submitter must belong to the team linked to this Workspace Team"
                )

    class Meta:
        verbose_name = "entry"
        verbose_name_plural = "entries"
        ordering = ["-submitted_at", "-created_at"]
        permissions = [
            ("upload_attachments", "Can upload attachments to entries"),
            ("review_entries", "Can review and approve entries"),
            ("flag_entries", "Can flag or comment on entries"),
        ]

    def __str__(self):
        return f"{self.entry_id} - {self.entry_type} - {self.amount} - {self.status}"
