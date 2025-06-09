
from django.db import models


class StatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"
    CLOSED = "closed", "Closed"
