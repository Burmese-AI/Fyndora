from django.db import models

class AuditActionType(models.TextChoices):
    TEAM_MEMBER_ADDED = "team_member_added", "Team Member Added"
    ENTRY_CREATED = "entry_created", "Entry Created"
    ENTRY_UPDATED = "entry_updated", "Entry Updated"
    STATUS_CHANGED = "status_changed", "Status Changed"
    FLAGGED = "flagged", "Flagged"
    FILE_UPLOADED = "file_uploaded", "File Uploaded"
