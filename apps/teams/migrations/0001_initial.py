# Generated by Django 5.2.1 on 2025-06-10 04:32

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0004_remove_organization_unique_organization_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Team",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "team_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "custom_remittance_rate",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Overrides workspace default if set (percentage value between 0 and 100)",
                        max_digits=5,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.00")),
                            django.core.validators.MaxValueValidator(Decimal("100.00")),
                        ],
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_teams",
                        to="organizations.organizationmember",
                    ),
                ),
                (
                    "team_coordinator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="coordinated_teams",
                        to="organizations.organizationmember",
                    ),
                ),
            ],
            options={
                "verbose_name": "team",
                "verbose_name_plural": "teams",
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(fields=("title",), name="unique_team")
                ],
            },
        ),
    ]
