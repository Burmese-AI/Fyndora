"""
Factories for auditlog app models.
"""

import uuid
from datetime import datetime, timezone
import factory
from factory.django import DjangoModelFactory
from factory import SubFactory

from apps.auditlog.models import AuditTrail
from apps.auditlog.constants import (
    AUDIT_ACTION_TYPE_CHOICES,
    AUDIT_TARGET_ENTITY_TYPE_CHOICES,
)
from .user_factories import CustomUserFactory


class AuditTrailFactory(DjangoModelFactory):
    """Factory for creating AuditTrail instances."""

    class Meta:
        model = AuditTrail

    audit_id = factory.LazyFunction(uuid.uuid4)
    user = SubFactory(CustomUserFactory)
    action_type = factory.Iterator([choice[0] for choice in AUDIT_ACTION_TYPE_CHOICES])
    target_entity = factory.LazyFunction(uuid.uuid4)
    target_entity_type = factory.Iterator(
        [choice[0] for choice in AUDIT_TARGET_ENTITY_TYPE_CHOICES]
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "action_by": obj.user.username if obj.user else "System",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Performed {obj.action_type} on {obj.target_entity_type}",
        }
    )


class EntryCreatedAuditFactory(AuditTrailFactory):
    """Factory for entry creation audit logs."""

    action_type = "entry_created"
    target_entity_type = "entry"
    metadata = factory.LazyAttribute(
        lambda obj: {
            "entry_type": "income",
            "amount": "1000.00",
            "submitter": obj.user.username if obj.user else "Unknown",
            "workspace": str(uuid.uuid4()),
        }
    )


class StatusChangedAuditFactory(AuditTrailFactory):
    """Factory for status change audit logs."""

    action_type = "status_changed"
    target_entity_type = "entry"
    metadata = factory.LazyAttribute(
        lambda obj: {
            "old_status": "pending",
            "new_status": "approved",
            "reviewer": obj.user.username if obj.user else "System",
            "reason": "Meets all requirements",
        }
    )


class FlaggedAuditFactory(AuditTrailFactory):
    """Factory for flagged entity audit logs."""

    action_type = "flagged"
    metadata = factory.LazyAttribute(
        lambda obj: {
            "flag_reason": "Requires additional review",
            "flagged_by": obj.user.username if obj.user else "System",
            "severity": "medium",
        }
    )


class FileUploadedAuditFactory(AuditTrailFactory):
    """Factory for file upload audit logs."""

    action_type = "file_uploaded"
    target_entity_type = "attachment"
    metadata = factory.LazyAttribute(
        lambda obj: {
            "filename": "document.pdf",
            "file_size": "2048",
            "uploaded_by": obj.user.username if obj.user else "Unknown",
            "file_type": "application/pdf",
        }
    )


class SystemAuditFactory(AuditTrailFactory):
    """Factory for system-generated audit logs."""

    user = None  # System actions have no user
    target_entity_type = "system"
    metadata = factory.LazyAttribute(
        lambda obj: {
            "system_action": f"Automated {obj.action_type}",
            "triggered_by": "system_cron",
            "execution_time": datetime.now(timezone.utc).isoformat(),
        }
    )


class AuditWithComplexMetadataFactory(AuditTrailFactory):
    """Factory for audit logs with complex metadata structures."""

    metadata = factory.LazyAttribute(
        lambda obj: {
            "user_details": {
                "username": obj.user.username if obj.user else "System",
                "user_id": str(obj.user.user_id) if obj.user else None,
                "ip_address": "192.168.1.100",
            },
            "entity_details": {
                "entity_type": obj.target_entity_type,
                "entity_id": str(obj.target_entity),
                "previous_values": {"status": "draft", "amount": "500.00"},
                "new_values": {"status": "submitted", "amount": "750.00"},
            },
            "context": {
                "workspace_id": str(uuid.uuid4()),
                "team_id": str(uuid.uuid4()),
                "organization_id": str(uuid.uuid4()),
            },
        }
    )


class BulkAuditTrailFactory(AuditTrailFactory):
    """Factory for creating multiple audit trail entries efficiently."""

    @classmethod
    def create_batch_for_entity(cls, entity_id, entity_type, count=5, **kwargs):
        """Create multiple audit entries for the same entity."""
        return cls.create_batch(
            count, target_entity=entity_id, target_entity_type=entity_type, **kwargs
        )

    @classmethod
    def create_workflow_sequence(cls, user, entity_id, entity_type="entry"):
        """Create a sequence of audit logs representing a typical workflow."""
        workflow_steps = [
            {
                "action_type": "entry_created",
                "metadata": {
                    "status": "draft",
                    "created_by": user.username,
                    "entry_type": "income",
                },
            },
            {
                "action_type": "status_changed",
                "metadata": {
                    "old_status": "draft",
                    "new_status": "submitted",
                    "submitted_by": user.username,
                },
            },
            {
                "action_type": "status_changed",
                "metadata": {
                    "old_status": "submitted",
                    "new_status": "approved",
                    "approved_by": user.username,
                    "approval_reason": "All requirements met",
                },
            },
        ]

        audit_logs = []
        for step in workflow_steps:
            audit_log = cls.create(
                user=user,
                target_entity=entity_id,
                target_entity_type=entity_type,
                **step,
            )
            audit_logs.append(audit_log)

        return audit_logs
