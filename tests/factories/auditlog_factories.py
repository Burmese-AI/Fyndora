"""
Factories for auditlog app models.
"""

import uuid

import factory
from django.contrib.contenttypes.models import ContentType
from factory import SubFactory
from factory.django import DjangoModelFactory

from apps.auditlog.constants import AuditActionType
from apps.auditlog.models import AuditTrail

from .user_factories import CustomUserFactory


class AuditTrailFactory(DjangoModelFactory):
    """Factory for creating AuditTrail instances."""

    class Meta:
        model = AuditTrail

    audit_id = factory.LazyFunction(uuid.uuid4)
    user = SubFactory(CustomUserFactory)
    action_type = factory.Iterator([choice[0] for choice in AuditActionType.choices])
    # Accept a model instance as target_entity and extract ContentType and PK
    target_entity = None
    target_entity_id = factory.LazyAttribute(
        lambda o: o.target_entity.pk if o.target_entity else None
    )
    target_entity_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.target_entity)
        if o.target_entity
        else None
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "action_by": obj.user.username if obj.user else "System",
            "details": f"Performed {obj.action_type} on {obj.target_entity_type}",
        }
    )


class EntryCreatedAuditFactory(AuditTrailFactory):
    """Factory for entry creation audit logs."""

    action_type = AuditActionType.ENTRY_CREATED
    target_entity_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.target_entity)
        if o.target_entity
        else ContentType.objects.get(app_label="entries", model="entry")
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "entry_type": "income",
            "amount": "1000.00",
            "submitter": obj.user.username if obj.user else "Unknown",
            "workspace_id": str(obj.target_entity.workspace.pk)
            if obj.target_entity and hasattr(obj.target_entity, "workspace")
            else str(uuid.uuid4()),
        }
    )


class StatusChangedAuditFactory(AuditTrailFactory):
    """Factory for status change audit logs."""

    action_type = AuditActionType.ENTRY_STATUS_CHANGED
    target_entity_type = factory.LazyAttribute(
        lambda obj: ContentType.objects.get(model="entry")
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "old_status": "pending",
            "new_status": "approved",
            "reviewer": obj.user.username if obj.user else "System",
            "reason": "Meets all requirements",
        }
    )


class EntryUpdatedAuditFactory(AuditTrailFactory):
    """Factory for entry update audit logs."""

    action_type = AuditActionType.ENTRY_UPDATED
    target_entity_type = factory.LazyAttribute(
        lambda obj: ContentType.objects.get(model="entry")
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "old_values": {"amount": "1000.00", "description": "Old description"},
            "new_values": {"amount": "1500.00", "description": "Updated description"},
            "updated_by": obj.user.username if obj.user else "System",
            "reason": "Data correction",
        }
    )


class FlaggedAuditFactory(AuditTrailFactory):
    """Factory for flagged entity audit logs."""

    action_type = AuditActionType.ENTRY_FLAGGED
    metadata = factory.LazyAttribute(
        lambda obj: {
            "flag_reason": "Requires additional review",
            "flagged_by": obj.user.username if obj.user else "System",
            "severity": "medium",
        }
    )


class FileUploadedAuditFactory(AuditTrailFactory):
    """Factory for file upload audit logs."""

    action_type = AuditActionType.FILE_UPLOADED
    target_entity_type = factory.LazyAttribute(
        lambda obj: ContentType.objects.get(model="attachment")
    )
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
    # There is currently no System model; if one is implemented later, its ContentType can be used here. For now, system actions are not tied to any specific model, so target_entity_type is set to None
    target_entity_type = None
    metadata = factory.LazyAttribute(
        lambda obj: {
            "system_action": f"Automated {obj.action_type}",
            "triggered_by": "system_cron",
        }
    )


class OrganizationCreatedAuditFactory(AuditTrailFactory):
    """Factory for organization creation audit logs."""

    action_type = AuditActionType.ORGANIZATION_CREATED
    target_entity_type = factory.LazyAttribute(
        lambda obj: ContentType.objects.get(
            app_label="organizations", model="organization"
        )
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "organization_name": "Test Organization",
            "created_by": obj.user.username if obj.user else "System",
            "initial_status": "active",
        }
    )


class WorkspaceCreatedAuditFactory(AuditTrailFactory):
    """Factory for workspace creation audit logs."""

    action_type = AuditActionType.WORKSPACE_CREATED
    target_entity_type = factory.LazyAttribute(
        lambda obj: ContentType.objects.get(app_label="workspaces", model="workspace")
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "workspace_name": "Test Workspace",
            "created_by": obj.user.username if obj.user else "System",
            "organization_id": str(uuid.uuid4()),
        }
    )


class TeamMemberAddedAuditFactory(AuditTrailFactory):
    """Factory for team member addition audit logs."""

    action_type = AuditActionType.TEAM_MEMBER_ADDED
    target_entity_type = factory.LazyAttribute(
        lambda obj: ContentType.objects.get(app_label="teams", model="team")
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "member_username": "new_member",
            "added_by": obj.user.username if obj.user else "System",
            "role": "member",
            "team_id": str(uuid.uuid4()),
        }
    )


class AuthenticationAuditFactory(AuditTrailFactory):
    """Factory for authentication-related audit logs."""

    action_type = AuditActionType.LOGIN_SUCCESS
    target_entity_type = factory.LazyAttribute(
        lambda obj: ContentType.objects.get(app_label="accounts", model="customuser")
    )
    metadata = factory.LazyAttribute(
        lambda obj: {
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 Test Browser",
            "login_method": "password",
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
                "entity_type": str(obj.target_entity_type)
                if obj.target_entity_type
                else None,
                "entity_id": str(obj.target_entity_id)
                if obj.target_entity_id
                else None,
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
    def create_batch_for_entity(cls, entity, count=5, **kwargs):
        """Create multiple audit entries for the same entity (model instance preferred)."""

        if hasattr(entity, "pk"):
            target_entity_id = entity.pk
            target_entity_type = ContentType.objects.get_for_model(entity)
        else:
            # fallback for UUID (legacy)
            target_entity_id = entity
            target_entity_type = ContentType.objects.get(model="entry")
        return cls.create_batch(
            count,
            target_entity=entity,
            target_entity_id=target_entity_id,
            target_entity_type=target_entity_type,
            **kwargs,
        )

    @classmethod
    def create_workflow_sequence(cls, user, entity, entity_type="entry"):
        """Create a sequence of audit logs representing a typical workflow (model instance preferred)."""

        if hasattr(entity, "pk"):
            target_entity_id = entity.pk
            target_entity_type = ContentType.objects.get_for_model(entity)
        else:
            # fallback for UUID (legacy)
            target_entity_id = entity
            target_entity_type = ContentType.objects.get(model="entry")
        workflow_steps = [
            {
                "action_type": AuditActionType.ENTRY_CREATED,
                "metadata": {
                    "status": "draft",
                    "created_by": user.username,
                    "entry_type": "income",
                },
            },
            {
                "action_type": AuditActionType.ENTRY_STATUS_CHANGED,
                "metadata": {
                    "old_status": "draft",
                    "new_status": "submitted",
                    "submitted_by": user.username,
                },
            },
            {
                "action_type": AuditActionType.ENTRY_STATUS_CHANGED,
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
                target_entity=entity,
                target_entity_id=target_entity_id,
                target_entity_type=target_entity_type,
                **step,
            )
            audit_logs.append(audit_log)

        return audit_logs
