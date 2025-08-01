# Generated by Django 5.2.1 on 2025-07-15 05:37

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0008_alter_organization_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="organization",
            options={
                "ordering": ["-created_at"],
                "permissions": (
                    ("add_workspace", "Can add workspace"),
                    ("view_all_workspaces", "Can view all workspaces"),
                ),
                "verbose_name": "organization",
                "verbose_name_plural": "organizations",
            },
        ),
    ]
