# Generated by Django 5.2.1 on 2025-07-16 10:26

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0001_initial"),
        ("organizations", "0011_organizationexchangerate"),
        ("workspaces", "0014_alter_workspace_end_date"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkspaceExchangeRate",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "rate",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.00")),
                            django.core.validators.MaxValueValidator(Decimal("999.99")),
                        ],
                    ),
                ),
                (
                    "effective_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False, unique=True
                    ),
                ),
                ("is_approved", models.BooleanField(default=False)),
                ("note", models.TextField(blank=True, null=True)),
                (
                    "workspace_exchange_rate_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "added_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_added_%(class)s_set",
                        to="organizations.organizationmember",
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_approved_%(class)s_set",
                        to="organizations.organizationmember",
                    ),
                ),
                (
                    "currency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(app_label)s_%(class)s_related",
                        related_query_name="%(app_label)s_%(class)s",
                        to="currencies.currency",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workspace_exchange_rates",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Workspace Exchange Rate",
                "verbose_name_plural": "Workspace Exchange Rates",
            },
        ),
    ]
