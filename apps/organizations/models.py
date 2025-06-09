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
    title = models.CharField(max_length=255)
    organization_owner = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="organization_owner"
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
        verbose_name = "orrganization"
        verbose_name_plural = "organizations"
        ordering = ["-created_at"]
        unique_together = ("organization_owner", "title")

    def __str__(self):
        return self.title
