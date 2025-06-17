# Create your models here.

from django.db import models
import uuid
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.core.models import baseModel
from apps.organizations.constants import StatusChoices
from django.conf import settings


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
