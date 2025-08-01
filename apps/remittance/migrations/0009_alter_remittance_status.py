# Generated by Django 5.2.1 on 2025-07-30 06:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "remittance",
            "0008_remove_remittance_remittance__due_dat_b70eef_idx_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="remittance",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("partial", "Partially Paid"),
                    ("paid", "Paid"),
                    ("overdue", "Overdue"),
                    ("canceled", "Canceled"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
