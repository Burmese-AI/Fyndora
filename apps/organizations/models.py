# Create your models here.

from django.db import models
import uuid
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.core.models import baseModel
from apps.accounts.models import CustomUser
from apps.organizations.constants import StatusChoices


class Organization(baseModel):
    organization_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    title = models.CharField(max_length=255, null=False, blank=False)
    organization_owner = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="owned_organizations"
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )
    description = models.TextField(blank=True, null=True)
    organization_expense = models.DecimalField(
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
                fields=["organization_owner", "title"],
                name="unique_organization",
            )
        ]

    def __str__(self):
        return self.title + " - " + self.organization_owner.username


class OrganizationMember(baseModel):
    organization_member_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization_id = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members"
    )
    user_id = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="organization_memberships"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "organization member"
        verbose_name_plural = "organization members"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "user_id"],
                name="unique_organization_member",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id.username} in {self.organization_id.title}"
