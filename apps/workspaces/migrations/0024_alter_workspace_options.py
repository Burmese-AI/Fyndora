# Generated by Django 5.2.1 on 2025-07-25 02:41

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "workspaces",
            "0023_remove_workspaceexchangerate_unique_workspace_exchange_rate_and_more",
        ),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="workspace",
            options={
                "ordering": ["-created_at"],
                "permissions": (
                    (
                        "assign_teams",
                        "Can assign teams to workspace by WA and Org Owner",
                    ),
                    ("lock_workspace", "Can lock workspace"),
                    ("view_dashboard", "Can view dashboard"),
                    (
                        "add_workspace_entry",
                        "Can add workspace entry by WA and Org Owner",
                    ),
                    (
                        "change_workspace_entry",
                        "Can change workspace entry by WA and Org Owner",
                    ),
                    (
                        "delete_workspace_entry",
                        "Can delete workspace entry by WA and Org Owner",
                    ),
                    (
                        "view_workspace_entry",
                        "Can view workspace entry by WA and Org Owner",
                    ),
                    (
                        "review_workspace_entry",
                        "Can review workspace entry by WA and Org Owner",
                    ),
                    (
                        "upload_workspace_attachments",
                        "Can upload workspace attachments by WA and Org Owner",
                    ),
                    (
                        "flag_workspace_entry",
                        "Can flag workspace entry by WA and Org Owner",
                    ),
                    ("export_workspace_report", "Can export workspace report"),
                    (
                        "change_workspace_currency",
                        "Can change workspace currency by WA and Org Owner",
                    ),
                ),
                "verbose_name": "workspace",
                "verbose_name_plural": "workspaces",
            },
        ),
    ]
