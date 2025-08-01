# Generated by Django 5.2.1 on 2025-07-25 17:24

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("currencies", "0007_alter_currency_code"),
        ("organizations", "0024_alter_organizationexchangerate_rate"),
        ("teams", "0009_alter_team_options"),
        ("workspaces", "0027_alter_workspaceexchangerate_rate"),
    ]

    operations = [
        migrations.CreateModel(
            name="Entry",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "entry_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("income", "Income"),
                            ("disbursement", "Disbursement"),
                            ("remittance", "Remittance"),
                            ("workspace_exp", "Workspace Expense"),
                            ("org_exp", "Organization Expense"),
                        ],
                        max_length=20,
                    ),
                ),
                ("description", models.CharField(max_length=255)),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                ("occurred_at", models.DateField()),
                (
                    "exchange_rate_used",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("reviewed", "Reviewed"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("status_last_updated_at", models.DateTimeField()),
                ("status_note", models.TextField(blank=True, null=True)),
                ("is_flagged", models.BooleanField(default=False)),
                (
                    "currency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entries",
                        to="currencies.currency",
                    ),
                ),
                (
                    "last_status_modified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="status_modified_entries",
                        to="organizations.organizationmember",
                    ),
                ),
                (
                    "org_exchange_rate_ref",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entries",
                        to="organizations.organizationexchangerate",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="organizations.organization",
                    ),
                ),
                (
                    "submitted_by_org_member",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entries",
                        to="organizations.organizationmember",
                    ),
                ),
                (
                    "submitted_by_team_member",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entries",
                        to="teams.teammember",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="workspaces.workspace",
                    ),
                ),
                (
                    "workspace_exchange_rate_ref",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entries",
                        to="workspaces.workspaceexchangerate",
                    ),
                ),
                (
                    "workspace_team",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="workspaces.workspaceteam",
                    ),
                ),
            ],
            options={
                "verbose_name": "entry",
                "verbose_name_plural": "entries",
                "ordering": ["-occurred_at", "-created_at"],
                "permissions": [
                    ("upload_attachments", "Can upload attachments to entries"),
                    ("review_entries", "Can review and approve entries"),
                    ("flag_entries", "Can flag or comment on entries"),
                ],
                "indexes": [
                    models.Index(
                        fields=["organization"], name="entries_ent_organiz_e92370_idx"
                    ),
                    models.Index(
                        fields=["workspace"], name="entries_ent_workspa_31f650_idx"
                    ),
                    models.Index(
                        fields=["workspace_team"], name="entries_ent_workspa_33834f_idx"
                    ),
                    models.Index(
                        fields=["occurred_at"], name="entries_ent_occurre_e5fce9_idx"
                    ),
                    models.Index(
                        fields=["status_last_updated_at"],
                        name="entries_ent_status__59feaa_idx",
                    ),
                    models.Index(
                        fields=["status"], name="entries_ent_status_e7314c_idx"
                    ),
                    models.Index(
                        fields=["submitted_by_org_member"],
                        name="entries_ent_submitt_56c38e_idx",
                    ),
                    models.Index(
                        fields=["submitted_by_team_member"],
                        name="entries_ent_submitt_b9ecab_idx",
                    ),
                    models.Index(
                        fields=["org_exchange_rate_ref"],
                        name="entries_ent_org_exc_56ca6e_idx",
                    ),
                    models.Index(
                        fields=["workspace_exchange_rate_ref"],
                        name="entries_ent_workspa_33f8ba_idx",
                    ),
                ],
            },
        ),
    ]
