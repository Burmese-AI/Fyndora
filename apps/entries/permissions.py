from django.db import models


class EntryPermissions(models.TextChoices):
    """
    Permissions for the Entry model.
    """

    ADD_ENTRY = "workspaces.add_workspace_entry", "Can add entry to workspace"
    CHANGE_ENTRY = "workspaces.change_workspace_entry", "Can change entry in workspace"
    DELETE_ENTRY = "workspaces.delete_workspace_entry", "Can delete entry in workspace"
    VIEW_ENTRY = "workspaces.view_workspace_entry", "Can view entry in workspace"
    REVIEW_ENTRY = "workspaces.review_workspace_entry", "Can review entry in workspace"
    UPLOAD_ATTACHMENTS = (
        "workspaces.upload_workspace_attachments",
        "Can upload attachments in workspace",
    )
    FLAG_ENTRY = "workspaces.flag_workspace_entry", "Can flag entry in workspace"
