from uuid import uuid4
from decimal import Decimal
from iso4217 import Currency as ISO4217Currency

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone  # this is causing ruff error , but neglected for now

from apps.core.models import SoftDeleteModel, baseModel


class Currency(baseModel, SoftDeleteModel):
    currency_id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=100, blank=True, null=True)
    # Note: Field Level constraint can't be conditional
    # That's why, its unique constraint is defined at model (table) level in Meta class
    code = models.CharField(max_length=3)

    def clean(self):
        super().clean()
        self.code = self.code.upper()
        try:
            self.name = ISO4217Currency(self.code).currency_name
        except Exception:
            raise ValidationError({"code": "Invalid currency code."})

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name_plural = "Currencies"
        constraints = [
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_currency_code",
            )
        ]


class ExchangeRateBaseModel(baseModel):
    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)s",
    )
    rate = models.DecimalField(
        max_digits=10,  # 0.00 - 999999999.99
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )
    effective_date = models.DateField(
        default=timezone.now,
    )
    added_by = models.ForeignKey(
        "organizations.OrganizationMember",
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(app_label)s_added_%(class)s_set",
    )
    note = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.currency.code == "MMK":
            self.is_approved = True
            if self.added_by:
                self.approved_by = self.added_by
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["currency", "effective_date"]),
        ]
