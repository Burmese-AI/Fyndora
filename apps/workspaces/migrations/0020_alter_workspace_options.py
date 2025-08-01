# Generated by Django 5.2.1 on 2025-07-24 01:33

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workspaces", "0019_alter_workspaceexchangerate_approved_by"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="workspace",
            options={
                "ordering": ["-created_at"],
                "permissions": (
                    ("assign_teams", "Can assign teams to workspace"),
                    ("lock_workspace", "Can lock workspace"),
                    ("view_dashboard", "Can view dashboard reports"),
                    ("add_workspace_entry", "Can add entry to workspace"),
                    ("change_workspace_entry", "Can change entry in workspace"),
                    ("delete_workspace_entry", "Can delete entry in workspace"),
                    ("view_workspace_entry", "Can view entry in workspace"),
                    ("review_workspace_entry", "Can review entry in workspace"),
                    (
                        "upload_workspace_attachments",
                        "Can upload attachments in workspace",
                    ),
                    ("flag_workspace_entry", "Can flag entry in workspace"),
                    ("export_workspace_report", "Can export workspace report"),
                ),
                "verbose_name": "workspace",
                "verbose_name_plural": "workspaces",
            },
        ),
    ]
