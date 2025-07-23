"""
Business audit logger for manual audit logging operations.
"""

import logging

from django.utils import timezone

from apps.auditlog.constants import AuditActionType
from apps.auditlog.services import (
    audit_create,
    audit_create_security_event,
)

from .config import AuditConfig
from .utils import safe_audit_log

logger = logging.getLogger(__name__)


class BusinessAuditLogger:
    """
    Enhanced helper class for manual business logic audit logging.
    Use this for complex operations that require rich context.
    """

    @staticmethod
    def _validate_request_and_user(request, user):
        """Validate request and user objects"""
        if not user or not user.is_authenticated:
            raise ValueError("Valid authenticated user required for audit logging")

    @staticmethod
    def _extract_request_metadata(request):
        """Extract metadata from Django request object"""
        if request is None:
            return {
                "ip_address": "unknown",
                "user_agent": "unknown", 
                "http_method": "unknown",
                "request_path": "unknown",
                "session_key": None,
                "source": "service_call"
            }
        
        return {
            "ip_address": request.META.get("REMOTE_ADDR", "unknown"),
            "user_agent": request.META.get("HTTP_USER_AGENT", "unknown"),
            "http_method": request.method,
            "request_path": request.path,
            "session_key": getattr(request.session, "session_key", None),
            "source": "web_request"
        }

    @staticmethod
    @safe_audit_log
    def log_entry_action(user, entry, action, request=None, **kwargs):
        """Log entry workflow actions with rich business context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        action_mapping = {
            "submit": AuditActionType.ENTRY_SUBMITTED,
            "review": AuditActionType.ENTRY_REVIEWED,
            "approve": AuditActionType.ENTRY_APPROVED,
            "reject": AuditActionType.ENTRY_REJECTED,
            "flag": AuditActionType.ENTRY_FLAGGED,
            "unflag": AuditActionType.ENTRY_UNFLAGGED,
        }

        if action not in action_mapping:
            logger.warning(f"Unknown entry workflow action: {action}")
            return

        metadata = {
            "entry_id": entry.id,
            "entry_type": entry.type,
            "entry_amount": str(entry.amount) if hasattr(entry, "amount") else None,
            "workspace_id": entry.workspace.id,
            "workspace_name": entry.workspace.name,
            "organization_id": entry.workspace.organization.id,
            "action": action,
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

        # Add action-specific metadata
        if action == "approve":
            metadata.update(
                {
                    "approver_id": user.id,
                    "approver_email": user.email,
                    "approval_notes": request.POST.get("notes", "") if request else kwargs.get("notes", ""),
                    "approval_level": request.POST.get("level", "standard") if request else kwargs.get("level", "standard"),
                    "approval_timestamp": timezone.now().isoformat(),
                }
            )
        elif action == "reject":
            metadata.update(
                {
                    "rejector_id": user.id,
                    "rejector_email": user.email,
                    "rejection_reason": request.POST.get("reason", "") if request else kwargs.get("reason", ""),
                    "rejection_notes": request.POST.get("notes", "") if request else kwargs.get("notes", ""),
                    "can_resubmit": request.POST.get("can_resubmit", True) if request else kwargs.get("can_resubmit", True),
                    "rejection_timestamp": timezone.now().isoformat(),
                }
            )
        elif action in ["flag", "unflag"]:
            metadata.update(
                {
                    "flag_reason": request.POST.get("reason", "") if request else kwargs.get("reason", ""),
                    "flag_notes": request.POST.get("notes", "") if request else kwargs.get("notes", ""),
                    "flag_severity": request.POST.get("severity", "medium") if request else kwargs.get("severity", "medium"),
                }
            )

        audit_create(
            user=user,
            action_type=action_mapping[action],
            target_entity=entry,
            metadata=metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_permission_change(user, target_user, permission, action, request=None, **kwargs):
        """Log permission changes with full context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        if action not in ["grant", "revoke"]:
            logger.warning(f"Unknown permission action: {action}")
            return

        audit_create_security_event(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED
            if action == "grant"
            else AuditActionType.PERMISSION_REVOKED,
            target_entity=target_user,
            metadata={
                "target_user_id": target_user.id,
                "target_user_email": target_user.email,
                "permission": permission,
                "action": action,
                "change_reason": request.POST.get("reason", "") if request else kwargs.get("reason", ""),
                "effective_date": request.POST.get(
                    "effective_date", timezone.now().isoformat()
                ) if request else kwargs.get("effective_date", timezone.now().isoformat()),
                "manual_logging": True,
                **BusinessAuditLogger._extract_request_metadata(request),
            },
        )

    @staticmethod
    @safe_audit_log
    def log_data_export(user, export_type, filters, result_count, request=None, **kwargs):
        """Log data export operations with detailed context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        audit_create(
            user=user,
            action_type=AuditActionType.DATA_EXPORTED,
            metadata={
                "export_type": export_type,
                "export_filters": filters,
                "result_count": result_count,
                "export_format": request.GET.get("format", "csv") if request else kwargs.get("format", "csv"),
                "export_reason": request.POST.get("reason", "business_analysis") if request else kwargs.get("reason", "business_analysis"),
                "file_size_estimate": f"{result_count * 100}B",  # Rough estimate
                "manual_logging": True,
                **BusinessAuditLogger._extract_request_metadata(request),
            },
        )

    @staticmethod
    @safe_audit_log
    def log_bulk_operation(user, operation_type, affected_objects, request=None, **kwargs):
        """Log bulk operations with intelligent object ID handling"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        object_count = len(affected_objects)

        # Use configuration-based thresholds
        if object_count <= AuditConfig.BULK_OPERATION_THRESHOLD:
            # Log all object IDs for smaller operations
            object_ids = [str(obj.id) for obj in affected_objects]
        else:
            # Log sample for large operations
            sample_size = min(AuditConfig.BULK_SAMPLE_SIZE, object_count)
            sample_objects = affected_objects[:sample_size]
            object_ids = [str(obj.id) for obj in sample_objects]

        audit_create(
            user=user,
            action_type=AuditActionType.BULK_OPERATION,
            metadata={
                "operation_type": operation_type,
                "total_objects": object_count,
                "object_ids": object_ids,
                "is_sample": object_count > AuditConfig.BULK_OPERATION_THRESHOLD,
                "sample_size": len(object_ids)
                if object_count > AuditConfig.BULK_OPERATION_THRESHOLD
                else None,
                "operation_reason": request.POST.get("reason", "") if request else kwargs.get("reason", ""),
                "manual_logging": True,
                **BusinessAuditLogger._extract_request_metadata(request),
                **kwargs,
            },
        )

    @staticmethod
    @safe_audit_log
    def log_status_change(user, entity, old_status, new_status, request=None, **kwargs):
        """Log status changes for any entity"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        audit_create(
            user=user,
            action_type=AuditActionType.STATUS_CHANGED,
            target_entity=entity,
            metadata={
                "entity_type": entity.__class__.__name__,
                "entity_id": entity.id,
                "old_status": old_status,
                "new_status": new_status,
                "status_change_reason": request.POST.get("reason", "") if request else kwargs.get("reason", ""),
                "manual_logging": True,
                **BusinessAuditLogger._extract_request_metadata(request),
                **kwargs,
            },
        )

    @staticmethod
    @safe_audit_log
    def log_file_operation(user, file_obj, operation, request=None, **kwargs):
        """Log file operations (upload, download, delete)"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        operation_mapping = {
            "upload": AuditActionType.FILE_UPLOADED,
            "download": AuditActionType.FILE_DOWNLOADED,
            "delete": AuditActionType.FILE_DELETED,
        }

        if operation not in operation_mapping:
            logger.warning(f"Unknown file operation: {operation}")
            return

        metadata = {
            "file_name": getattr(file_obj, "name", "unknown"),
            "file_size": getattr(file_obj, "size", 0),
            "file_type": getattr(file_obj, "content_type", "unknown"),
            "operation": operation,
            "file_category": kwargs.get("file_category", "general"),
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
        }

        # Add operation-specific metadata
        if operation == "upload":
            metadata.update(
                {
                    "upload_source": request.POST.get("source", "web_interface") if request else kwargs.get("source", "web_interface"),
                    "upload_purpose": request.POST.get("purpose", "") if request else kwargs.get("purpose", ""),
                }
            )
        elif operation == "download":
            metadata.update(
                {
                    "download_reason": request.POST.get("reason", "") if request else kwargs.get("reason", ""),
                }
            )

        audit_create(
            user=user,
            action_type=operation_mapping[operation],
            target_entity=file_obj if hasattr(file_obj, "id") else None,
            metadata=metadata,
        )
