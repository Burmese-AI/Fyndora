"""
Business audit logger for manual audit logging operations.
"""

import logging

from django.utils import timezone

from apps.auditlog.constants import AuditActionType
from apps.auditlog.config import AuditConfig
from apps.auditlog.services import (
    audit_create,
    audit_create_security_event,
    make_json_serializable,
)

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
            "session_key": getattr(getattr(request, "session", None), "session_key", None),
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
            "entry_id": str(entry.entry_id),
            "entry_type": entry.entry_type,
            "entry_amount": str(entry.amount) if hasattr(entry, "amount") else None,
            "workspace_id": str(entry.workspace.workspace_id),
            "workspace_name": entry.workspace.title,
            "organization_id": str(entry.workspace.organization.organization_id),
            "action": action,
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

        # Add action-specific metadata
        if action == "approve":
            metadata.update(
                {
                    "approver_id": str(user.user_id),
                    "approver_email": user.email,
                    "approval_notes": request.POST.get("notes", "") if request else kwargs.get("notes", ""),
                    "approval_level": request.POST.get("level", "standard") if request else kwargs.get("level", "standard"),
                    "approval_timestamp": timezone.now().isoformat(),
                }
            )
        elif action == "reject":
            metadata.update(
                {
                    "rejector_id": str(user.user_id),
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

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=action_mapping[action],
            target_entity=entry,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_permission_change(user, target_user, permission, action, request=None, **kwargs):
        """Log permission changes with full context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        if action not in ["grant", "revoke"]:
            logger.warning(f"Unknown permission action: {action}")
            return

        metadata = {
            "target_user_id": str(target_user.user_id),
            "target_user_email": target_user.email,
            "permission": permission,
            "action": action,
            "change_reason": request.POST.get("reason", "") if request else kwargs.get("reason", ""),
            "effective_date": request.POST.get(
                "effective_date", timezone.now().isoformat()
            ) if request else kwargs.get("effective_date", timezone.now().isoformat()),
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
        }

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create_security_event(
            user=user,
            action_type=AuditActionType.PERMISSION_GRANTED
            if action == "grant"
            else AuditActionType.PERMISSION_REVOKED,
            target_entity=target_user,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_data_export(user, export_type, filters, result_count, request=None, **kwargs):
        """Log data export operations with detailed context"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        # Ensure filters are JSON serializable
        serializable_filters = make_json_serializable(filters or {})

        metadata = {
            "export_type": export_type,
            "export_filters": serializable_filters,
            "result_count": result_count,
            "export_format": request.GET.get("format", "csv") if request else kwargs.get("format", "csv"),
            "export_reason": request.POST.get("reason", "business_analysis") if request else kwargs.get("reason", "business_analysis"),
            "file_size_estimate": f"{result_count * 100}B",  # Rough estimate
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
        }

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=AuditActionType.DATA_EXPORTED,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_bulk_operation(user, operation_type, affected_objects, request=None, **kwargs):
        """Log bulk operations with sampling for large datasets"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        # Sample object IDs for large operations
        object_ids = []
        for obj in affected_objects:
            # Get the primary key value, handling different field names
            pk_field = obj._meta.pk.name
            pk_value = getattr(obj, pk_field)
            object_ids.append(str(pk_value))
        
        total_objects = len(object_ids)
        
        # Use AuditConfig values for threshold and sampling
        if total_objects > AuditConfig.BULK_OPERATION_THRESHOLD:
            # For large operations, sample only the first N objects
            sampled_ids = object_ids[:AuditConfig.BULK_SAMPLE_SIZE]
        else:
            # For small operations, include all object IDs
            sampled_ids = object_ids

        metadata = {
            "operation_type": operation_type,
            "total_objects": total_objects,
            "object_ids": sampled_ids,
            "operation_criteria": request.POST.get("criteria", "manual_selection") if request else kwargs.get("criteria", "manual_selection"),
            "batch_size": request.POST.get("batch_size", total_objects) if request else kwargs.get("batch_size", total_objects),
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=AuditActionType.BULK_OPERATION,
            metadata=serializable_metadata,
        )

    @staticmethod
    @safe_audit_log
    def log_status_change(user, entity, old_status, new_status, request=None, **kwargs):
        """Log status changes for any entity"""
        BusinessAuditLogger._validate_request_and_user(request, user)

        metadata = {
            "entity_type": entity.__class__.__name__,
            "entity_id": str(getattr(entity, entity._meta.pk.name)),
            "old_status": old_status,
            "new_status": new_status,
            "status_change_reason": request.POST.get("reason", "") if request else kwargs.get("reason", ""),
            "manual_logging": True,
            **BusinessAuditLogger._extract_request_metadata(request),
            **kwargs,
        }

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=AuditActionType.STATUS_CHANGED,
            target_entity=entity,
            metadata=serializable_metadata,
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

        # Ensure all metadata is JSON serializable
        serializable_metadata = make_json_serializable(metadata)

        audit_create(
            user=user,
            action_type=operation_mapping[operation],
            target_entity=file_obj if hasattr(file_obj, '_meta') and hasattr(file_obj._meta, 'pk') else None,
            metadata=serializable_metadata,
        )
