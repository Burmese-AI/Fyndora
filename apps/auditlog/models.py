import uuid

from django.conf import settings
from django.db import models

from .constants import AUDIT_ACTION_TYPE_CHOICES, AUDIT_TARGET_ENTITY_TYPE_CHOICES


class AuditTrail(models.Model):
    """
    Stores a record of user or system actions for auditing purposes.
    """

    audit_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action_type = models.CharField(max_length=100, choices=AUDIT_ACTION_TYPE_CHOICES)
    target_entity = models.UUIDField()
    target_entity_type = models.CharField(
        max_length=100, choices=AUDIT_TARGET_ENTITY_TYPE_CHOICES
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.action_type} by {self.user} on {self.target_entity_type}:{self.target_entity} at {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["target_entity_type", "target_entity"]),
            models.Index(fields=["action_type"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user"]),
        ]
