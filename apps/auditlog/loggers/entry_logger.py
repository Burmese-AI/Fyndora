"""Entry-specific audit logger for entry workflow and status operations."""

import logging
from typing import Any, Dict, Optional

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.utils import timezone

from apps.auditlog.constants import AuditActionType
from apps.auditlog.utils import safe_audit_log
from apps.entries.models import Entry

from .base_logger import BaseAuditLogger
from .metadata_builders import (
    EntityMetadataBuilder,
    WorkflowMetadataBuilder,
)

logger = logging.getLogger(__name__)


class EntryAuditLogger(BaseAuditLogger):
    """Audit logger for entry-related operations."""

    def get_supported_actions(self) -> Dict[str, str]:
        """Return mapping of supported entry actions to audit action types."""
        return {
            "submit": AuditActionType.ENTRY_SUBMITTED,
            "review": AuditActionType.ENTRY_REVIEWED,
            "approve": AuditActionType.ENTRY_APPROVED,
            "reject": AuditActionType.ENTRY_REJECTED,
            "flag": AuditActionType.ENTRY_FLAGGED,
            "unflag": AuditActionType.ENTRY_UNFLAGGED,
            "update": AuditActionType.ENTRY_UPDATED,
            "delete": AuditActionType.ENTRY_DELETED,
        }

    def get_logger_name(self) -> str:
        """Return the name of this logger for identification."""
        return "entry_logger"

    @safe_audit_log
    def log_entry_workflow_action(
        self,
        user: User,
        entry: Entry,
        action: str,
        request: Optional[HttpRequest] = None,
        workflow_stage: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log entry workflow actions with rich business context."""
        # Map workflow actions to audit action types
        workflow_action_mapping = {
            "submit": AuditActionType.ENTRY_SUBMITTED,
            "approve": AuditActionType.ENTRY_APPROVED,
            "reject": AuditActionType.ENTRY_REJECTED,
        }

        action_type = self._handle_action_with_mapping(
            user, entry, action, workflow_action_mapping, request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata with workflow flag
        metadata = self._build_base_metadata(action, request, **kwargs)

        # Add entry-specific metadata
        metadata.update(EntityMetadataBuilder.build_entry_metadata(entry))

        # Add workflow metadata
        # Extract notes and reason from kwargs to avoid duplicate keyword arguments
        workflow_kwargs = kwargs.copy()
        notes = workflow_kwargs.pop("notes", "")
        reason = workflow_kwargs.pop("reason", "")
        
        metadata.update(
            WorkflowMetadataBuilder.build_workflow_metadata(
                user,
                action,
                workflow_stage,
                notes=notes,
                reason=reason,
                **workflow_kwargs,
            )
        )

        # Finalize and create audit log
        workspace = getattr(entry, "workspace", None)
        self._finalize_and_create_audit(user, action_type, metadata, entry, workspace)

    @safe_audit_log
    def log_entry_action(
        self,
        user: User,
        entry: Entry,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log entry actions with rich business context."""
        action_type = self._handle_action_with_mapping(
            user, entry, action, self.get_supported_actions(), request, **kwargs
        )
        if action_type is None:
            return

        # Build base metadata
        metadata = self._build_base_metadata(action, request, **kwargs)

        # Add entry-specific metadata
        metadata.update(EntityMetadataBuilder.build_entry_metadata(entry))

        # Add action-specific metadata
        if action == "approve":
            metadata.update(
                {
                    "approver_id": str(user.user_id),
                    "approver_email": user.email,
                    "approval_notes": self._get_request_param(request, "notes")
                    or kwargs.get("notes", ""),
                    "approval_level": self._get_request_param(request, "level")
                    or kwargs.get("level", "standard"),
                    "approval_timestamp": timezone.now().isoformat(),
                }
            )
        elif action == "reject":
            metadata.update(
                {
                    "rejector_id": str(user.user_id),
                    "rejector_email": user.email,
                    "rejection_reason": self._get_request_param(request, "reason")
                    or kwargs.get("reason", ""),
                    "rejection_notes": self._get_request_param(request, "notes")
                    or kwargs.get("notes", ""),
                    "can_resubmit": self._get_request_param(request, "can_resubmit")
                    or kwargs.get("can_resubmit", True),
                    "rejection_timestamp": timezone.now().isoformat(),
                }
            )
        elif action in ["flag", "unflag"]:
            metadata.update(
                {
                    "flag_reason": self._get_request_param(request, "reason")
                    or kwargs.get("reason", ""),
                    "flag_notes": self._get_request_param(request, "notes")
                    or kwargs.get("notes", ""),
                    "flag_severity": self._get_request_param(request, "severity")
                    or kwargs.get("severity", "medium"),
                }
            )
        elif action == "update":
            metadata.update(
                {
                    "updater_id": str(user.user_id),
                    "updater_email": user.email,
                    "updated_fields": kwargs.get("updated_fields", []),
                    "original_values": kwargs.get("original_values", {}),
                    "new_values": kwargs.get("new_values", {}),
                    "update_reason": self._get_request_param(request, "reason")
                    or kwargs.get("reason", ""),
                    "update_timestamp": timezone.now().isoformat(),
                }
            )
        elif action == "delete":
            metadata.update(
                {
                    "deleter_id": str(user.user_id),
                    "deleter_email": user.email,
                    "deletion_reason": self._get_request_param(request, "reason")
                    or kwargs.get("reason", ""),
                    "soft_delete": kwargs.get("soft_delete", False),
                    "deletion_timestamp": timezone.now().isoformat(),
                    "entry_status_at_deletion": kwargs.get("entry_status", "unknown"),
                }
            )

        # Finalize and create audit log
        workspace = getattr(entry, "workspace", None)
        self._finalize_and_create_audit(user, action_type, metadata, entry, workspace)

    @safe_audit_log
    def log_status_change(
        self,
        user: User,
        entity: Any,
        old_status: str,
        new_status: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log status changes for any entity."""
        self._validate_request_and_user(request, user)

        metadata = {
            "entity_type": entity.__class__.__name__,
            "entity_id": str(getattr(entity, entity._meta.pk.name)),
            "old_status": old_status,
            "new_status": new_status,
            "status_change_reason": self._get_request_param(request, "reason")
            or kwargs.get("reason", ""),
            "manual_logging": True,
            **self._extract_request_metadata(request),
            **kwargs,
        }

        # Finalize and create audit log
        workspace = getattr(entity, "workspace", None)
        self._finalize_and_create_audit(
            user, AuditActionType.ENTRY_STATUS_CHANGED, metadata, entity, workspace
        )
