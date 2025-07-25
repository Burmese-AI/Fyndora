# Generated by Django 5.2.1 on 2025-07-24 13:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0005_currency_created_at_currency_updated_at"),
        ("organizations", "0022_alter_organization_options"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="organizationexchangerate",
            name="unique_organization_exchange_rate",
        ),
        migrations.AddField(
            model_name="organizationexchangerate",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="organizationexchangerate",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("organization", "currency", "effective_date"),
                name="unique_organization_exchange_rate",
            ),
        ),
    ]
