from django.db import models


class EntryPermissions(models.TextChoices):
    """
    Permissions for the Entry model.
    """

    ADD_ENTRY = "workspaces.add_entry", "Can add entry to workspace"
    CHANGE_ENTRY = "workspaces.change_entry", "Can change entry in workspace"
    DELETE_ENTRY = "workspaces.delete_entry", "Can delete entry in workspace"
    VIEW_ENTRY = "workspaces.view_entry", "Can view entry in workspace"
    REVIEW_ENTRY = "workspaces.review_entry", "Can review entry in workspace"
    UPLOAD_ATTACHMENTS = (
        "workspaces.upload_attachments",
        "Can upload attachments in workspace",
    )
    FLAG_ENTRY = "workspaces.flag_entry", "Can flag entry in workspace"
