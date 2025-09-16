import json
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from .config import AuditConfig
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
    target_entity_id = models.UUIDField(null=True, blank=True)
    target_entity_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    target_entity = GenericForeignKey("target_entity_type", "target_entity_id")
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_trails",
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_trails",
    )

    def _parse_metadata(self):
        """Parse metadata ensuring it's a dictionary."""
        if not self.metadata:
            return {}

        # Handle legacy string-based JSON metadata
        if isinstance(self.metadata, str):
            try:
                return json.loads(self.metadata)
            except json.JSONDecodeError:
                return {"raw_data": self.metadata}

        # JSONField should already be parsed, but ensure it's a dict
        if isinstance(self.metadata, dict):
            return self.metadata

        # Handle other types
        return {"value": str(self.metadata)}

    @property
    def details(self):
        """
        Generate simple human-readable details from metadata.
        """
        if not self.metadata:
            return "No details provided."

        # Handle string metadata
        if isinstance(self.metadata, str):
            return self.metadata

        metadata = self._parse_metadata()
        if not metadata:
            return "No details provided."

        # Simple status change formatting
        if "old_status" in metadata and "new_status" in metadata:
            old = metadata.get("old_status", "N/A")
            new = metadata.get("new_status", "N/A")
            return f"Status: {old} → {new}"

        # Show only the most important fields
        important_fields = [
            "status",
            "amount",
            "title",
            "name",
            "email",
            "username",
            "entity_type",
            "operation_type",
            "reason",
        ]

        details = []
        for field in important_fields:
            if field in metadata and metadata[field]:
                value = str(metadata[field])[:50]  # Limit length
                details.append(f"{field.replace('_', ' ').title()}: {value}")

        return "; ".join(details) if details else "Action completed"

    def is_expired(self) -> bool:
        """
        Check if this audit log has exceeded its retention period.
        """
        now = timezone.now()
        retention_days = AuditConfig.get_retention_days_for_action(self.action_type)
        cutoff_date = now - timedelta(days=retention_days)

        return self.timestamp < cutoff_date

    def __str__(self):
        return f"{self.action_type} by {self.user} on {self.target_entity_type}:{self.target_entity_id} at {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["target_entity_type", "target_entity_id"]),
            models.Index(fields=["action_type"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["workspace"]),
        ]
