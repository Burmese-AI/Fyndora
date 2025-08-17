"""System-specific audit logger for permissions, bulk operations, and system events."""

import logging
from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.utils import timezone

from apps.auditlog.constants import AuditActionType
from apps.auditlog.utils import safe_audit_log

from .base_logger import BaseAuditLogger
from .metadata_builders import (
    FileMetadataBuilder,
)

logger = logging.getLogger(__name__)


class SystemAuditLogger(BaseAuditLogger):
    """Audit logger for system-level operations."""

    def get_supported_actions(self) -> Dict[str, str]:
        """Return mapping of supported system actions to audit action types."""
        return {
            "permission_grant": AuditActionType.PERMISSION_GRANTED,
            "permission_revoke": AuditActionType.PERMISSION_REVOKED,
            "permission_change": AuditActionType.PERMISSION_CHANGED,
            "bulk_operation": AuditActionType.BULK_OPERATION,
            "data_export": AuditActionType.DATA_EXPORTED,
            "file_upload": AuditActionType.FILE_UPLOADED,
            "file_download": AuditActionType.FILE_DOWNLOADED,
            "file_delete": AuditActionType.FILE_DELETED,
            "operation_failure": AuditActionType.OPERATION_FAILED,
        }

    def get_logger_name(self) -> str:
        """Return the name of this logger for identification."""
        return "system_logger"

    @safe_audit_log
    def log_permission_change(
        self,
        user: User,
        target_user: User,
        permission_type: str,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log permission changes with detailed context."""
        self._validate_request_and_user(request, user)

        action_mapping = {
            "grant": AuditActionType.PERMISSION_GRANTED,
            "revoke": AuditActionType.PERMISSION_REVOKED,
            "change": AuditActionType.PERMISSION_CHANGED,
        }

        if action not in action_mapping:
            logger.warning(f"Unknown permission action: {action}")
            return

        # Build metadata for permission changes
        metadata = {
            "action": action,
            "permission_type": permission_type,
            "manual_logging": True,
            **self._extract_request_metadata(request),
            **kwargs,
        }

        # Add target user metadata
        metadata.update(
            {
                "target_user_id": str(target_user.user_id),
                "target_user_email": target_user.email,
                "grantor_id": str(user.user_id),
                "grantor_email": user.email,
                "permission_timestamp": timezone.now().isoformat(),
            }
        )

        # Add action-specific metadata
        if action == "grant":
            metadata.update(
                {
                    "granted_permissions": kwargs.get("granted_permissions", []),
                    "grant_reason": kwargs.get("reason", ""),
                }
            )
        elif action == "revoke":
            metadata.update(
                {
                    "revoked_permissions": kwargs.get("revoked_permissions", []),
                    "revoke_reason": kwargs.get("reason", ""),
                }
            )
        elif action == "change":
            metadata.update(
                {
                    "previous_permissions": kwargs.get("previous_permissions", []),
                    "new_permissions": kwargs.get("new_permissions", []),
                    "change_reason": kwargs.get("reason", ""),
                }
            )

        # Finalize and create audit log
        self._finalize_and_create_audit(
            user, action_mapping[action], metadata, target_user
        )

    @safe_audit_log
    def log_data_export(
        self,
        user: User,
        export_type: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log data export operations with detailed context."""
        self._validate_request_and_user(request, user)

        # Build metadata for data export
        metadata = {
            "action": "data_export",
            "export_type": export_type,
            "manual_logging": True,
            **self._extract_request_metadata(request),
            **kwargs,
        }

        # Add export-specific metadata
        metadata.update(
            {
                "exporter_id": str(user.user_id),
                "exporter_email": user.email,
                "export_timestamp": timezone.now().isoformat(),
                "export_format": kwargs.get("export_format", ""),
                "record_count": kwargs.get("record_count", 0),
                "file_size": kwargs.get("file_size", ""),
                "export_filters": kwargs.get("export_filters", {}),
                "export_columns": kwargs.get("export_columns", []),
            }
        )

        # Finalize and create audit log
        self._finalize_and_create_audit(
            user, AuditActionType.DATA_EXPORTED, metadata, None
        )

    @safe_audit_log
    def log_bulk_operation(
        self,
        user: User,
        operation_type: str,
        affected_entities: List[Any],
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log bulk operations with sampling for large datasets."""
        self._validate_request_and_user(request, user)

        # Build metadata for bulk operations
        metadata = {
            "action": "bulk_operation",
            "operation_type": operation_type,
            "manual_logging": True,
            **self._extract_request_metadata(request),
            **kwargs,
        }

        # Add bulk operation metadata
        metadata.update(
            {
                "operator_id": str(user.user_id),
                "operator_email": user.email,
                "operation_timestamp": timezone.now().isoformat(),
                "total_affected_count": len(affected_entities),
                "operation_status": kwargs.get("status", "completed"),
                "operation_duration": kwargs.get("duration", ""),
            }
        )

        # Sample entities for large operations (limit to 10 for performance)
        if len(affected_entities) > 10:
            sampled_entities = affected_entities[:10]
            metadata["sampled_entities"] = [
                {"id": str(getattr(entity, "pk", "")), "type": type(entity).__name__}
                for entity in sampled_entities
            ]
            metadata["sampling_note"] = (
                f"Showing first 10 of {len(affected_entities)} entities"
            )
        else:
            metadata["affected_entities"] = [
                {"id": str(getattr(entity, "pk", "")), "type": type(entity).__name__}
                for entity in affected_entities
            ]

        # Finalize and create audit log
        self._finalize_and_create_audit(
            user, AuditActionType.BULK_OPERATION_PERFORMED, metadata, None
        )

    @safe_audit_log
    def log_file_operation(
        self,
        user: User,
        file_obj: Any,
        action: str,
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log file operations (upload, download, delete) with detailed context."""
        self._validate_request_and_user(request, user)

        action_mapping = {
            "upload": AuditActionType.FILE_UPLOADED,
            "download": AuditActionType.FILE_DOWNLOADED,
            "delete": AuditActionType.FILE_DELETED,
        }

        if action not in action_mapping:
            logger.warning(f"Unknown file operation action: {action}")
            return

        # Build base metadata
        metadata = {
            "action": action,
            "manual_logging": True,
            **self._extract_request_metadata(request),
            **kwargs,
        }

        # Add file-specific metadata
        metadata.update(
            FileMetadataBuilder.build_file_metadata(file_obj, action, user, **kwargs)
        )

        # Finalize and create audit log
        self._finalize_and_create_audit(
            user, action_mapping[action], metadata, file_obj
        )

    @safe_audit_log
    def log_operation_failure(
        self,
        user: Optional[User],
        operation: str,
        error_details: Dict[str, Any],
        request: Optional[HttpRequest] = None,
        **kwargs,
    ) -> None:
        """Log system operation failures and errors."""
        # Build metadata for operation failures
        metadata = {
            "action": "operation_failure",
            "operation": operation,
            "manual_logging": True,
            **self._extract_request_metadata(request),
            **kwargs,
        }

        # Add failure-specific metadata
        metadata.update(
            {
                "failure_timestamp": timezone.now().isoformat(),
                "error_type": error_details.get("error_type", ""),
                "error_message": error_details.get("error_message", ""),
                "error_code": error_details.get("error_code", ""),
                "stack_trace": error_details.get("stack_trace", ""),
                "affected_component": error_details.get("affected_component", ""),
                "severity": error_details.get("severity", "medium"),
            }
        )

        # Add user context if available
        if user:
            metadata.update(
                {
                    "user_id": str(user.user_id),
                    "user_email": user.email,
                }
            )
        else:
            metadata.update(
                {
                    "user_id": "system",
                    "user_email": "system@internal",
                }
            )

        # Finalize and create audit log
        self._finalize_and_create_audit(
            user, AuditActionType.OPERATION_FAILED, metadata, None
        )
