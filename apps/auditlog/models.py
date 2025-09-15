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

    def _format_status_change(self, metadata):
        """Format status change details."""
        old = metadata.get("old_status", "N/A")
        new = metadata.get("new_status", "N/A")
        return f"Status changed from '{old}' to '{new}'"

    def _format_authentication_event(self, metadata):
        """Format authentication event details."""
        if self.action_type == AuditActionType.LOGIN_SUCCESS:
            method = metadata.get("login_method", "unknown")
            return f"Successful login via {method}"
        elif self.action_type == AuditActionType.LOGIN_FAILED:
            username = metadata.get("attempted_username", "unknown")
            reason = metadata.get("failure_reason", "unknown")
            return f"Failed login attempt for '{username}' - {reason}"
        elif self.action_type == AuditActionType.LOGOUT:
            return "User logged out"
        return self._format_generic(metadata)

    def _format_crud_operation(self, metadata):
        """Format CRUD operation details."""
        details = []

        # Add entity information
        if "entity_type" in metadata:
            details.append(f"Entity: {metadata['entity_type']}")

        # Add workspace context
        if "workspace_id" in metadata:
            details.append(f"Workspace: {metadata['workspace_id']}")

        # Add specific field changes
        if "changed_fields" in metadata:
            fields = metadata["changed_fields"]
            if isinstance(fields, list):
                details.append(f"Changed fields: {', '.join(fields)}")

        # Add old/new values if available
        if "old_values" in metadata and "new_values" in metadata:
            old_vals = metadata["old_values"]
            new_vals = metadata["new_values"]
            if isinstance(old_vals, dict) and isinstance(new_vals, dict):
                changes = []
                for field in old_vals.keys():
                    if field in new_vals and old_vals[field] != new_vals[field]:
                        changes.append(
                            f"{field}: '{old_vals[field]}' → '{new_vals[field]}'"
                        )
                if changes:
                    details.append(f"Changes: {'; '.join(changes)}")

        return "; ".join(details) if details else self._format_generic(metadata)

    def _format_bulk_operation(self, metadata):
        """Format bulk operation details."""
        operation = metadata.get("operation_type", "unknown")
        count = metadata.get("affected_count", 0)
        object_types = metadata.get("object_types", [])

        details = [f"Bulk {operation} operation"]
        details.append(f"Affected items: {count}")

        if object_types:
            types_str = ", ".join(object_types)
            details.append(f"Types: {types_str}")

        return "; ".join(details)

    def _format_workflow_action(self, metadata):
        """Format entry workflow action details."""
        action_details = []

        if "previous_status" in metadata and "new_status" in metadata:
            action_details.append(
                f"Status: {metadata['previous_status']} → {metadata['new_status']}"
            )

        if "reviewer" in metadata:
            action_details.append(f"Reviewer: {metadata['reviewer']}")

        if "comments" in metadata:
            action_details.append(f"Comments: {metadata['comments']}")

        if "reason" in metadata:
            action_details.append(f"Reason: {metadata['reason']}")

        return (
            "; ".join(action_details)
            if action_details
            else self._format_generic(metadata)
        )

    def _format_generic(self, metadata):
        """Generic formatter for metadata."""
        if not metadata:
            return "No additional details"

        # Filter out technical/internal fields
        display_fields = {
            k: v
            for k, v in metadata.items()
            if not k.startswith("_") and k not in ["automatic_logging", "timestamp"]
        }

        if not display_fields:
            return "No additional details"

        formatted_parts = []
        for key, value in display_fields.items():
            formatted_key = key.replace("_", " ").title()

            # Handle nested dictionaries
            if isinstance(value, dict):
                # For nested dictionaries, just include the section title
                formatted_parts.append(f"{formatted_key}:")
            else:
                # For simple values, include key: value
                formatted_parts.append(f"{formatted_key}: {value}")

        return "; ".join(formatted_parts)

    @property
    def details(self):
        """
        Generate human-readable details from metadata based on action type.
        """
        # Handle special cases where metadata should be returned as-is
        if isinstance(self.metadata, str):
            try:
                # Try to parse as JSON
                parsed_metadata = json.loads(self.metadata)
                # If successful, continue with normal processing
                metadata = parsed_metadata if isinstance(parsed_metadata, dict) else {}
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw string
                return self.metadata
        else:
            metadata = self._parse_metadata()

        if not metadata:
            return "No details provided."

        # Action-specific formatters
        formatters = {
            # Authentication events
            AuditActionType.LOGIN_SUCCESS: self._format_authentication_event,
            AuditActionType.LOGIN_FAILED: self._format_authentication_event,
            AuditActionType.LOGOUT: self._format_authentication_event,
            # Status change events
            AuditActionType.ORGANIZATION_STATUS_CHANGED: self._format_status_change,
            AuditActionType.WORKSPACE_STATUS_CHANGED: self._format_status_change,
            AuditActionType.ENTRY_STATUS_CHANGED: self._format_status_change,
            AuditActionType.REMITTANCE_STATUS_CHANGED: self._format_status_change,
            # Generic status change (for backward compatibility and tests)
            "status_changed": self._format_status_change,
            # Entry workflow actions
            AuditActionType.ENTRY_SUBMITTED: self._format_workflow_action,
            AuditActionType.ENTRY_REVIEWED: self._format_workflow_action,
            AuditActionType.ENTRY_APPROVED: self._format_workflow_action,
            AuditActionType.ENTRY_REJECTED: self._format_workflow_action,
            AuditActionType.ENTRY_FLAGGED: self._format_workflow_action,
            AuditActionType.ENTRY_UNFLAGGED: self._format_workflow_action,
            # Bulk operations
            AuditActionType.BULK_OPERATION: self._format_bulk_operation,
        }

        # Check for CRUD operations
        crud_actions = [
            # Organization CRUD
            AuditActionType.ORGANIZATION_CREATED,
            AuditActionType.ORGANIZATION_UPDATED,
            AuditActionType.ORGANIZATION_DELETED,
            # Workspace CRUD
            AuditActionType.WORKSPACE_CREATED,
            AuditActionType.WORKSPACE_UPDATED,
            AuditActionType.WORKSPACE_DELETED,
            # Entry CRUD
            AuditActionType.ENTRY_CREATED,
            AuditActionType.ENTRY_UPDATED,
            AuditActionType.ENTRY_DELETED,
            # User CRUD
            AuditActionType.USER_CREATED,
            AuditActionType.USER_UPDATED,
            AuditActionType.USER_DELETED,
            # Team CRUD
            AuditActionType.TEAM_CREATED,
            AuditActionType.TEAM_UPDATED,
            AuditActionType.TEAM_DELETED,
            # Remittance CRUD
            AuditActionType.REMITTANCE_CREATED,
            AuditActionType.REMITTANCE_UPDATED,
            AuditActionType.REMITTANCE_DELETED,
        ]

        # Use appropriate formatter
        if self.action_type in formatters:
            return formatters[self.action_type](metadata)
        elif self.action_type in crud_actions:
            return self._format_crud_operation(metadata)
        else:
            return self._format_generic(metadata)

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
