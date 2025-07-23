from django.db import models


WORKSPACE_CONTEXT_OBJECT_NAME = "workspaces"
WORKSPACE_DETAIL_CONTEXT_OBJECT_NAME = "workspace"

class StatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"
    CLOSED = "closed", "Closed"
