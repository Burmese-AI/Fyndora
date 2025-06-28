from django.db import models


class EntryPermissions(models.TextChoices):
    """
    Permissions for the Entry model.
    """

    ADD_ENTRY = "entries.add_entry", "Can add entry"
    CHANGE_ENTRY = "entries.change_entry", "Can change entry"
    DELETE_ENTRY = "entries.delete_entry", "Can delete entry"
    VIEW_ENTRY = "entries.view_entry", "Can view entry"
    REVIEW_ENTRY = "entries.review_entry", "Can review entries"
    UPLOAD_ATTACHMENTS = "entries.upload_attachments", "Can upload attachments"
    FLAG_ENTRY = "entries.flag_entry", "Can flag entries"
