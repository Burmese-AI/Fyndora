# Generated by Django 5.2.1 on 2025-07-13 13:12

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workspaces", "0011_alter_workspace_options"),
    ]

    operations = [
        migrations.RenameField(
            model_name="workspace",
            old_name="operation_reviewer",
            new_name="operations_reviewer",
        ),
    ]
