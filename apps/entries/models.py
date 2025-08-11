import uuid
from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator

from apps.core.models import baseModel, SoftDeleteModel
from apps.currencies.models import Currency
from apps.entries.constants import EntryType, EntryStatus
from apps.teams.models import TeamMember
from apps.workspaces.models import Workspace, WorkspaceExchangeRate, WorkspaceTeam
from apps.organizations.models import (
    OrganizationMember,
    Organization,
    OrganizationExchangeRate,
)


class Entry(baseModel, SoftDeleteModel):
    entry_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    description = models.CharField(max_length=255)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="entries",
    )
    workspace_team = models.ForeignKey(
        WorkspaceTeam,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="entries",
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    occurred_at = models.DateField()
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    exchange_rate_used = models.DecimalField(
        max_digits=10,  # 0.00 - 999999999.99
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )
    org_exchange_rate_ref = models.ForeignKey(
        OrganizationExchangeRate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="entries",
    )
    workspace_exchange_rate_ref = models.ForeignKey(
        WorkspaceExchangeRate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="entries",
    )
    submitted_by_org_member = models.ForeignKey(
        OrganizationMember,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="entries",
    )

    submitted_by_team_member = models.ForeignKey(
        TeamMember,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="entries",
    )
    status = models.CharField(
        max_length=20, choices=EntryStatus.choices, default=EntryStatus.PENDING
    )
    status_last_updated_at = models.DateTimeField(null=True, blank=True)
    last_status_modified_by = models.ForeignKey(
        OrganizationMember,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="status_modified_entries",
    )
    status_note = models.TextField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False)

    @property
    def converted_amount(self):
        return self.amount * self.exchange_rate_used

    @property
    def submitter(self):
        """Return the submitter (either team member or organization member)."""
        if self.submitted_by_org_member:
            print(f"in model org => {self.submitted_by_org_member}")
            return self.submitted_by_org_member.user.username
        print(f"in model team => {self.submitted_by_team_member}")
        return self.submitted_by_team_member.organization_member.user.username

    def clean(self):
        super().clean()

    #     if not self.currency:
    #         raise ValidationError("Currency is required.")

    #     if not self.exchange_rate_used:
    #         raise ValidationError("Exchange rate used must be specified.")

    #     if not self.org_exchange_rate_ref and not self.workspace_exchange_rate_ref:
    #         raise ValidationError("Either organization or workspace exchange rate reference must be set.")

    #     super().clean()

    class Meta:
        verbose_name = "entry"
        verbose_name_plural = "entries"
        ordering = ["-occurred_at", "-created_at"]
        permissions = [
            ("upload_attachments", "Can upload attachments to entries"),
            ("review_entries", "Can review and approve entries"),
            ("flag_entries", "Can flag or comment on entries"),
        ]
        indexes = [
            # Context
            models.Index(fields=["organization"]),
            models.Index(fields=["workspace"]),
            models.Index(fields=["workspace_team"]),
            # Time
            models.Index(fields=["occurred_at"]),
            models.Index(fields=["status_last_updated_at"]),
            # Status
            models.Index(fields=["status"]),
            # Submitters
            models.Index(fields=["submitted_by_org_member"]),
            models.Index(fields=["submitted_by_team_member"]),
            # Exchange rate sources
            models.Index(fields=["org_exchange_rate_ref"]),
            models.Index(fields=["workspace_exchange_rate_ref"]),
        ]

    def __str__(self):
        return f"{self.pk} - {self.entry_type} - {self.amount} - {self.status}"
