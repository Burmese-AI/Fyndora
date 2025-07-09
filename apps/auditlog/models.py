import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .constants import AuditActionType


class AuditTrail(models.Model):
    """
    Stores a record of user or system actions for auditing purposes.
    """

    audit_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action_type = models.CharField(max_length=100, choices=AuditActionType.choices)
    target_entity_id = models.UUIDField()
    target_entity_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_entity = GenericForeignKey("target_entity_type", "target_entity_id")
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)

    @property
    def details(self):
        import json

        if not self.metadata:
            return "No details provided."

        metadata_dict = self.metadata
        if isinstance(self.metadata, str):
            try:
                metadata_dict = json.loads(self.metadata)
            except json.JSONDecodeError:
                return self.metadata  # Not a valid JSON string, return as is

        if not isinstance(metadata_dict, dict):
            return str(metadata_dict)  # Valid JSON, but not a dictionary

        if self.action_type == AuditActionType.STATUS_CHANGED:
            old = metadata_dict.get("old_status", "N/A")
            new = metadata_dict.get("new_status", "N/A")
            return f"Status changed from '{old}' to '{new}'."

        # Generic fallback for other action types
        return ", ".join(
            [
                f"{key.replace('_', ' ').title()}: {value}"
                for key, value in metadata_dict.items()
            ]
        )

    def __str__(self):
        return f"{self.action_type} by {self.user} on {self.target_entity_type}:{self.target_entity_id} at {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["target_entity_type", "target_entity_id"]),
            models.Index(fields=["action_type"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user"]),
        ]
