import uuid
from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation

from apps.core.models import baseModel
from apps.organizations.constants import StatusChoices
from apps.currencies.models import ExchangeRateBaseModel
from apps.core.permissions import OrganizationPermissions


class Organization(baseModel):
    organization_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    title = models.CharField(max_length=255, null=False, blank=False)
    owner = models.OneToOneField(
        "OrganizationMember",
        on_delete=models.CASCADE,
        related_name="owner",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )
    description = models.TextField(blank=True, null=True)
    expense = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "organization"
        verbose_name_plural = "organizations"
        ordering = ["-created_at"]
        permissions = (
            (OrganizationPermissions.ADD_WORKSPACE, OrganizationPermissions.ADD_WORKSPACE.label),
            (OrganizationPermissions.ADD_TEAM, OrganizationPermissions.ADD_TEAM.label),
            (OrganizationPermissions.INVITE_ORG_MEMBER, OrganizationPermissions.INVITE_ORG_MEMBER.label),
            (OrganizationPermissions.ADD_ORG_ENTRY, OrganizationPermissions.ADD_ORG_ENTRY.label),
            (OrganizationPermissions.VIEW_ORG_ENTRY, OrganizationPermissions.VIEW_ORG_ENTRY.label),
            (OrganizationPermissions.CHANGE_ORG_ENTRY, OrganizationPermissions.CHANGE_ORG_ENTRY.label),
            (OrganizationPermissions.DELETE_ORG_ENTRY, OrganizationPermissions.DELETE_ORG_ENTRY.label),
            (
                OrganizationPermissions.CHANGE_WORKSPACE_ADMIN,
                OrganizationPermissions.CHANGE_WORKSPACE_ADMIN.label,
            ),
        )
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "title"],
                name="unique_organization",
            )
        ]

    def __str__(self):
        return self.title


class OrganizationMember(baseModel):
    organization_member_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    is_active = models.BooleanField(default=True)
    entries = GenericRelation(
        "entries.Entry",
        content_type_field="submitter_content_type",
        object_id_field="submitter_object_id",
        related_query_name="organization_member_entries",
    )

    @property
    def is_org_owner(self):
        return self.organization.owner == self

    class Meta:
        verbose_name = "organization member"
        verbose_name_plural = "organization members"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_member",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} in {self.organization.title}"


class OrganizationExchangeRate(ExchangeRateBaseModel):
    organization_exchange_rate_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="organization_exchange_rates",
    )

    class Meta:
        verbose_name = "Organization Exchange Rate"
        verbose_name_plural = "Organization Exchange Rates"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "currency", "effective_date"],
                name="unique_organization_exchange_rate",
            )
        ]
