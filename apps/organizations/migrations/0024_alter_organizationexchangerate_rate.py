# Generated by Django 5.2.1 on 2025-07-25 17:24

import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "organizations",
            "0023_remove_organizationexchangerate_unique_organization_exchange_rate_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationexchangerate",
            name="rate",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
            ),
        ),
    ]
